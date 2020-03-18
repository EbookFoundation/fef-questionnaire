from django.conf.urls import include, url
from django.contrib import admin

import questionnaire
from questionnaire.page import views

admin.autodiscover()

urlpatterns = [
    url(r'^$', views.page, {'page_to_render' : 'index'}),
    url(r'q/', include('questionnaire.urls')),

    # admin
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
]
