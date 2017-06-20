from django.conf.urls import patterns, include, url
from django.contrib import admin

import questionnaire

admin.autodiscover()

urlpatterns = patterns('',
    
    url(r'^$', 'questionnaire.page.views.page', {'page_to_render' : 'index'}),
    url(r'q/', include('questionnaire.urls')),

    # admin
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
