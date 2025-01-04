from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.urls import re_path
from ajax_select import urls as ajax_select_urls

import artshow.views

admin.autodiscover()
admin.site.site_title = settings.SITE_NAME + ' Admin'
admin.site.site_header = settings.SITE_NAME + ' Admin'

urlpatterns = [
    re_path(r'^admin/lookups/', include(ajax_select_urls)),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^artshow/', include('artshow.urls')),
    re_path(r'^manage/', include('artshow.manage_urls')),
    re_path(r'^bid/', include('artshow.bid_urls')),
    re_path(r'^accounts/', include('tinyreg.urls')),
    # Uncomment when using the debug toolbar.
    # re_path(r'^__debug__/', include('debug_toolbar.urls')),
    re_path(r'^$', artshow.views.home, name="home"),
]

if settings.TEST_OAUTH_PROVIDER:
    urlpatterns.extend([
        re_path(r'^test/oauth/', include('tinyreg.tests.urls'))
    ])
