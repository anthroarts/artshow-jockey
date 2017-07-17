# Artshow Jockey
# Copyright (C) 2009, 2010 Chris Cogdon
# See file COPYING for licence details

from django.conf.urls import url

from . import announcement
from . import manage
from . import paypal
from . import register

urlpatterns = [
    url(r'^$', manage.index),
    url(r'^artist/(?P<artist_id>\d+)/$', manage.artist),
    url(r'^artist/(?P<artist_id>\d+)/artist/$', manage.artist_details),
    url(r'^artist/(?P<artist_id>\d+)/person/$', manage.person_details),
    url(r'^artist/(?P<artist_id>\d+)/pieces/$', manage.pieces),
    url(r'^artist/(?P<artist_id>\d+)/spaces/$', manage.spaces),
    url(r'^artist/(?P<artist_id>\d+)/downloadcsv/$', manage.downloadcsv),
    url(r'^artist/(?P<artist_id>\d+)/bidsheets/$', manage.bid_sheets),
    url(r'^artist/(?P<artist_id>\d+)/controlforms/$', manage.control_forms),
    url(r'^artist/(?P<artist_id>\d+)/makepayment/$', manage.make_payment),
    url(r'^artist/(?P<artist_id>\d+)/makepayment/complete/mail/$', manage.payment_made_mail),
    url(r'^artist/(?P<artist_id>\d+)/makepayment/complete/paypal/$', manage.payment_made_paypal),
    url(r'^artist/(?P<artist_id>\d+)/makepayment/cancelled/paypal/$', manage.payment_cancelled_paypal),
    url(r'^register/$', register.main),
    url(r'^ipn/$', paypal.ipn_handler),
    url(r'^announcement/$', announcement.index, name="view_announcements"),
    url(r'^announcement/(?P<announcement_id>\d+)/$', announcement.show),
]
