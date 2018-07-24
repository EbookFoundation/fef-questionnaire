import django.template 
from django.template import Template
register = django.template.Library()

@register.simple_tag(takes_context=True)
def render_with_landing(context, text):
    if not context.has_key('landing_object') and context.has_key('runinfo'):
        landing = context['runinfo'].landing
        context['landing_object'] = landing.content_object if landing else ''
    if text:
        template = Template(text)
        return template.render(context)
    
    else:
        return ''
        
