from django.conf.urls import include
from django.contrib import admin
from django.urls import re_path
from ajax_select import urls as ajax_select_urls

import artshow.views

admin.autodiscover()

urlpatterns = [
    re_path(r'^admin/lookups/', include(ajax_select_urls)),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^artshow/', include('artshow.urls')),
    re_path(r'^manage/', include('artshow.manage_urls')),
    re_path(r'^accounts/', include('tinyreg.urls')),
    re_path(r'^$', artshow.views.home, name="home"),
]
