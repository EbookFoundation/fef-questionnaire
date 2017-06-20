# vim: set fileencoding=utf-8

from django.conf.urls import *
from django.conf import settings
from .views import *
from .page.views import page, langpage

urlpatterns = [
    url(r'^$',
        questionnaire, name='questionnaire_noargs'),
    url(r'^csv/(?P<qid>\d+)/$',
        export_csv, name='export_csv'),
    url(r'^summary/(?P<qid>\d+)/$',
        export_summary, name='export_summary'),
    url(r'^(?P<runcode>[^/]+)/progress/$',
        get_async_progress, name='progress'),
    url(r'^take/(?P<questionnaire_id>[0-9]+)/$', generate_run),
    url(r'^$', page, {'page_to_render' : 'index'}),
    url(r'^(?P<page_to_render>.*)\.html$', page),
    url(r'^(?P<lang>..)/(?P<page_to_trans>.*)\.html$', langpage),
    url(r'^setlang/$', set_language),
    url(r'^landing/(?P<nonce>\w+)/$', QuestionnaireView.as_view(), name="landing"),
]

# item questionnaires
try:
    if settings.QUESTIONNAIRE_ITEM_MODEL and settings.QUESTIONNAIRE_SHOW_ITEM_RESULTS:
        urlpatterns += [
        url(r"^items/$", questionnaires, name="questionnaires"), 
        url(r"^new_questionnaire/(?P<item_id>\d*)/?$", new_questionnaire, name="new_questionnaire"),
        url(r"^items/answers_(?P<qid>\d+)_(?P<item_id>\d*).csv$", export_item_csv, name="questionnaire_answers"),
        url(r"^items/summary_(?P<qid>\d+)_(?P<item_id>\d*).csv$", export_item_summary, name="answer_summary"),
    ]
except AttributeError:
    pass

urlpatterns += [url(r'^(?P<runcode>[^/]+)/(?P<qs>[-]{0,1}\d+)/$', questionnaire, name='questionset')]

if not use_session:
    urlpatterns += [
        url(r'^(?P<runcode>[^/]+)/$',
            questionnaire, name='questionnaire'),
        url(r'^(?P<runcode>[^/]+)/(?P<qs>[-]{0,1}\d+)/prev/$',
            redirect_to_prev_questionnaire,
            name='redirect_to_prev_questionnaire'),
    ]
else:
    urlpatterns += [
        url(r'^$',
            questionnaire, name='questionnaire'),
        url(r'^prev/$',
            redirect_to_prev_questionnaire,
            name='redirect_to_prev_questionnaire')
    ]

