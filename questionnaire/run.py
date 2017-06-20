import re
from . import Processors, AnswerException
from .dependency_checker import dep_check
from .models import Answer, Question, RunInfo
from .parsers import BooleanParser, parse_checks
from .parsers import BoolNot, BoolAnd, BoolOr, Checker
from .request_cache import request_cache

def get_runinfo(random):
    "Return the RunInfo entry with the provided random key"
    res = RunInfo.objects.filter(random=random.lower())
    return res and res[0] or None


def get_question(number, questionset):
    "Return the specified Question (by number) from the specified Questionset"
    res = Question.objects.filter(number=number, questionset=questionset)
    return res and res[0] or None


def delete_answer(question, subject, run):
    "Delete the specified question/subject/run combination from the Answer table"
    Answer.objects.filter(subject=subject, run=run, question=question).delete()


def add_answer(runinfo, question, answer_dict):
    """
    Add an Answer to a Question for RunInfo, given the relevant form input

    answer_dict contains the POST'd elements for this question, minus the
    question_{number} prefix.  The question_{number} form value is accessible
    with the ANSWER key.
    """
    answer = Answer()
    answer.question = question
    answer.subject = runinfo.subject
    answer.run = runinfo.run

    type = question.get_type()

    if "ANSWER" not in answer_dict:
        answer_dict['ANSWER'] = None

    if type in Processors:
        answer.answer = Processors[type](question, answer_dict) or ''
    else:
        raise AnswerException("No Processor defined for question type %s" % type)

    # first, delete all existing answers to this question for this particular user+run
    delete_answer(question, runinfo.subject, runinfo.run)

    # then save the new answer to the database
    answer.save(runinfo)

    return True


def has_tag(tag, runinfo):
    """ Returns true if the given runinfo contains the given tag. """
    return tag in (t.strip() for t in runinfo.tags.split(','))


def check_parser(runinfo, exclude=[]):
    depparser = BooleanParser(dep_check, runinfo, {})
    tagparser = BooleanParser(has_tag, runinfo)

    fnmap = {
        "maleonly": lambda v: runinfo.subject.gender == 'male',
        "femaleonly": lambda v: runinfo.subject.gender == 'female',
        "shownif": lambda v: v and depparser.parse(v),
        "iftag": lambda v: v and tagparser.parse(v)
    }

    for ex in exclude:
        del fnmap[ex]

    @request_cache()
    def satisfies_checks(checks):
        if not checks:
            return True

        checks = parse_checks(checks)

        for check, value in checks.items():
            if check in fnmap:
                value = value and value.strip()
                if not fnmap[check](value):
                    return False

        return True

    return satisfies_checks


@request_cache()
def skipped_questions(runinfo):
    if not runinfo.skipped:
        return []

    return [s.strip() for s in runinfo.skipped.split(',')]


@request_cache()
def question_satisfies_checks(question, runinfo, checkfn=None):
    if question.number in skipped_questions(runinfo):
        return False

    checkfn = checkfn or check_parser(runinfo)
    return checkfn(question.checks)

@request_cache(keyfn=lambda *args: args[0].id)
def questionset_satisfies_checks(questionset, runinfo, checks=None):
    """Return True if the runinfo passes the checks specified in the QuestionSet

    Checks is an optional dictionary with the keys being questionset.pk and the
    values being the checks of the contained questions.

    This, in conjunction with fetch_checks allows for fewer
    db roundtrips and greater performance.

    Sadly, checks cannot be hashed and therefore the request cache is useless
    here. Thankfully the benefits outweigh the costs in my tests.
    """

    passes = check_parser(runinfo)

    if not passes(questionset.checks):
        return False

    if not checks:
        checks = dict()
        checks[questionset.id] = []

        for q in questionset.questions():
            checks[questionset.id].append((q.checks, q.number))

    # questionsets that pass the checks but have no questions are shown
    # (comments, last page, etc.)
    if not checks[questionset.id]:
        return True

    # if there are questions at least one needs to be visible
    for check, number in checks[questionset.id]:
        if number in skipped_questions(runinfo):
            continue

        if passes(check):
            return True

    return False


def get_progress(runinfo):
    position, total = 0, 0

    current = runinfo.questionset
    sets = current.questionnaire.questionsets()

    checks = fetch_checks(sets)

    # fetch the all question checks at once. This greatly improves the
    # performance of the questionset_satisfies_checks function as it
    # can avoid a roundtrip to the database for each question

    for qs in sets:
        if questionset_satisfies_checks(qs, runinfo, checks):
            total += 1

        if qs.id == current.id:
            position = total

    if not all((position, total)):
        progress = 1
    else:
        progress = float(position) / float(total) * 100.00

        # progress is always at least one percent
        progress = progress >= 1.0 and progress or 1

    return int(progress)


def fetch_checks(questionsets):
    ids = [qs.pk for qs in questionsets]

    query = Question.objects.filter(questionset__pk__in=ids)
    query = query.values('questionset_id', 'checks', 'number')

    checks = dict()
    for qsid in ids:
        checks[qsid] = list()

    for result in (r for r in query):
        checks[result['questionset_id']].append(
            (result['checks'], result['number'])
        )

    return checks


def recursivly_build_partially_evaluated_js_exp_for_shownif_check(treenode, runinfo, question):
    if isinstance(treenode, BoolNot):
        return "!( %s )" % recursivly_build_partially_evaluated_js_exp_for_shownif_check(treenode.arg, runinfo, question)
    elif isinstance(treenode, BoolAnd):
        return " && ".join(
            "( %s )" % recursivly_build_partially_evaluated_js_exp_for_shownif_check(arg, runinfo, question)
            for arg in treenode.args )
    elif isinstance(treenode, BoolOr):
        return " || ".join(
            "( %s )" % recursivly_build_partially_evaluated_js_exp_for_shownif_check(arg, runinfo, question)
            for arg in treenode.args )
    else:
        assert( isinstance(treenode, Checker) )
        # ouch, we're assuming the correct syntax is always found
        question_looksee_number = treenode.expr.split(",", 1)[0]
        if Question.objects.get(number=question_looksee_number).questionset \
           != question.questionset:
            return "true" if dep_check(treenode.expr, runinfo, {}) else "false"
        else:
            return str(treenode)


def make_partially_evaluated_js_exp_for_shownif_check(checkexpression, runinfo, question):
    depparser = BooleanParser(dep_check, runinfo, {})
    parsed_bool_expression_results = depparser.boolExpr.parseString(checkexpression)[0]
    return recursivly_build_partially_evaluated_js_exp_for_shownif_check(parsed_bool_expression_results, runinfo, question)


def substitute_answer(qvalues, obj):
    """Objects with a 'text/text_xx' attribute can contain magic strings
    referring to the answers of other questions. This function takes
    any such object, goes through the stored answers (qvalues) and replaces
    the magic string with the actual value. If this isn't possible the
    magic string is removed from the text.

    Only answers with 'store' in their check will work with this.

    """

    if qvalues and obj.text:
        magic = 'subst_with_ans_'
        regex = r'subst_with_ans_(\S+)'

        replacements = re.findall(regex, obj.text)
        text_attributes = [a for a in dir(obj) if a.startswith('text_')]

        for answerid in replacements:

            target = magic + answerid
            replacement = qvalues.get(answerid.lower(), '')

            for attr in text_attributes:
                oldtext = getattr(obj, attr)
                newtext = oldtext.replace(target, replacement)

                setattr(obj, attr, newtext)


