from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from ajax_select import urls as ajax_select_urls

import artshow.views

admin.autodiscover()

urlpatterns = [
    url(r'^admin/lookups/', include(ajax_select_urls)),
    url(r'^admin/', admin.site.urls),
    url(r'^artshow/', include('artshow.urls')),
    url(r'^manage/', include('artshow.manage_urls')),
    url(r'^peeps/', include('peeps.urls')),
    url(r'^accounts/', include('tinyreg.urls')),
    url(r'^$', artshow.views.home, name="home"),
]

urlpatterns += staticfiles_urlpatterns()
