# Artshow Jockey
# Copyright (C) 2009, 2010 Chris Cogdon
# See file COPYING for licence details

from django.conf.urls import url

from . import announcement
from . import manage
from . import paypal
from . import register

urlpatterns = [
    url(r'^$', manage.index, name='artshow-manage'),
    url(r'^artist/(?P<artist_id>\d+)/$', manage.artist,
        name='artshow-manage-artist'),
    url(r'^artist/(?P<artist_id>\d+)/artist/$', manage.artist_details,
        name='artshow-manage-artist-details'),
    url(r'^artist/(?P<artist_id>\d+)/person/$', manage.person_details,
        name='artshow-manage-person-details'),
    url(r'^artist/(?P<artist_id>\d+)/pieces/$', manage.pieces,
        name='artshow-manage-pieces'),
    url(r'^artist/(?P<artist_id>\d+)/spaces/$', manage.spaces,
        name='artshow-manage-spaces'),
    url(r'^artist/(?P<artist_id>\d+)/downloadcsv/$', manage.downloadcsv,
        name='artshow-manage-csv'),
    url(r'^artist/(?P<artist_id>\d+)/bidsheets/$', manage.bid_sheets,
        name='artshow-manage-bidsheets'),
    url(r'^artist/(?P<artist_id>\d+)/controlforms/$', manage.control_forms,
        name='artshow-manage-controlforms'),
    url(r'^artist/(?P<artist_id>\d+)/makepayment/$', manage.make_payment,
        name='artshow-manage-make-payment'),
    url(r'^artist/(?P<artist_id>\d+)/makepayment/complete/mail/$',
        manage.payment_made_mail, name='artshow-manage-payment-mail'),
    url(r'^artist/(?P<artist_id>\d+)/makepayment/complete/paypal/$',
        manage.payment_made_paypal, name='artshow-manage-payment-paypal'),
    url(r'^artist/(?P<artist_id>\d+)/makepayment/cancelled/paypal/$',
        manage.payment_cancelled_paypal,
        name='artshow-manage-payment-paypal-cancelled'),
    url(r'^register/$', register.main, name='artshow-register'),
    url(r'^ipn/$', paypal.ipn_handler),
    url(r'^announcement/$', announcement.index, name="view_announcements"),
    url(r'^announcement/(?P<announcement_id>\d+)/$', announcement.show,
        name='artshow-announcement'),
]
