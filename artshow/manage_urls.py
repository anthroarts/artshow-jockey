# Artshow Jockey
# Copyright (C) 2009, 2010 Chris Cogdon
# See file COPYING for licence details

from django.urls import re_path

from . import announcement
from . import manage
from . import register

urlpatterns = [
    re_path(r'^$', manage.index, name='artshow-manage'),
    re_path(r'^artist/(?P<artist_id>\d+)/$', manage.artist,
            name='artshow-manage-artist'),
    re_path(r'^artist/(?P<artist_id>\d+)/artist/$', manage.artist_details,
            name='artshow-manage-artist-details'),
    re_path(r'^artist/(?P<artist_id>\d+)/person/$', manage.person_details,
            name='artshow-manage-person-details'),
    re_path(r'^artist/(?P<artist_id>\d+)/pieces/$', manage.pieces,
            name='artshow-manage-pieces'),
    re_path(r'^artist/(?P<artist_id>\d+)/piece/$', manage.add_piece,
            name='artshow-manage-add-piece'),
    re_path(r'^artist/(?P<artist_id>\d+)/piece/(?P<piece_id>\d+)/$', manage.edit_piece,
            name='artshow-manage-edit-piece'),
    re_path(r'^artist/(?P<artist_id>\d+)/piece/(?P<piece_id>\d+)/delete/$', manage.delete_piece,
            name='artshow-manage-add-piece'),
    re_path(r'^artist/(?P<artist_id>\d+)/spaces/$', manage.spaces,
            name='artshow-manage-spaces'),
    re_path(r'^artist/(?P<artist_id>\d+)/downloadcsv/$', manage.downloadcsv,
            name='artshow-manage-csv'),
    re_path(r'^artist/(?P<artist_id>\d+)/bidsheets/$', manage.bid_sheets,
            name='artshow-manage-bidsheets'),
    re_path(r'^artist/(?P<artist_id>\d+)/controlforms/$', manage.control_forms,
            name='artshow-manage-controlforms'),
    re_path(r'^artist/(?P<artist_id>\d+)/makepayment/$', manage.make_payment,
            name='artshow-manage-make-payment'),
    re_path(r'^artist/(?P<artist_id>\d+)/makepayment/complete/mail/$',
            manage.payment_made_mail, name='artshow-manage-payment-mail'),
    re_path(r'^artist/(?P<artist_id>\d+)/makepayment/complete/square/$',
            manage.payment_made_square, name='artshow-manage-payment-square'),
    re_path(r'^artist/(?P<artist_id>\d+)/makepayment/error/square/$',
            manage.payment_error_square, name='artshow-manage-payment-square-error'),
    re_path(r'^register/$', register.main, name='artshow-register'),
    re_path(r'^announcement/$', announcement.index, name="view_announcements"),
    re_path(r'^announcement/(?P<announcement_id>\d+)/$', announcement.show,
            name='artshow-announcement'),
]
