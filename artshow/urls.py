# Artshow Jockey
# Copyright (C) 2009, 2010 Chris Cogdon
# See file COPYING for licence details

from django.conf.urls import url

from . import addbidder
from . import bid_entry
from . import bidderreg
from . import cashier
from . import csvreports
from . import pdfreports
from . import reports
from . import views
from . import voice_auction
from . import workflows

urlpatterns = [
    url(r'^$', views.index, name='artshow-home'),
    url(r'^entry/$', views.dataentry, name='artshow-dataentry'),
    url(r'^entry/bidders/$', addbidder.bulk_add,
        name='artshow-bulk-add-bidders'),
    url(r'^entry/bids/$', addbidder.bid_bulk_add,
        name='artshow-bulk-add-bids'),
    url(r'^entry/bids/mobile/$', bid_entry.bid_entry,
        name='artshow-mobile-bid-entry'),
    url(r'^entry/bids/(?P<artist_id>\d+)/(?P<piece_id>\d+)/$', bid_entry.bids),
    url(r'^entry/auction_bids/(?P<adult>[yn])/$', voice_auction.auction_bids),
    url(r'^entry/order_auction/(?P<adult>[yn])/$', voice_auction.order_auction,
        name='artshow-voice-auction-order'),
    url(r'^entry/find_bidder/$', addbidder.find_bidder,
        name='artshow-entry-bidder-lookup'),
    url(r'^entry/bidder/(?P<pk>\d+)/$', addbidder.bidder_detail,
        name='artshow-entry-bidder'),
    # url(r'^entry/bids/location/(?P<location>[^/]+)/$', bidentry.add_bids),
    url(r'^reports/$', reports.index, name='artshow-reports'),
    url(r'^artist/(?P<artist_id>\d+)/mailinglabel/$',
        views.artist_mailing_label),
    url(r'^artist/(?P<artist_id>\d+)/piecereport/$',
        reports.artist_piece_report),
    url(r'^reports/artists/$', reports.artists, name='artshow-report-artists'),
    url(r'^reports/winning-bidders/$', reports.winning_bidders,
        name='artshow-report-winning-bidders'),
    url(r'^reports/artist-panel-report/$', reports.artist_panel_report,
        name='artshow-report-artist-to-panel'),
    url(r'^reports/panel-artist-report/$', reports.panel_artist_report,
        name='artshow-report-panel-to-artist'),
    url(r'^reports/artist-payment-report/$', reports.artist_payment_report,
        name='artshow-report-artist-payment'),
    url(r'^reports/show-summary/$', reports.show_summary,
        name='artshow-summary'),
    url(r'^reports/voice-auction/$', reports.voice_auction,
        name='artshow-report-voice-auction'),
    url(r'^reports/sales-percentiles/$', reports.sales_percentiles,
        name='artshow-report-percentiles'),
    url(r'^reports/allocations-waiting/$', reports.allocations_waiting,
        name='artshow-report-allocations-waiting'),
    url(r'^cashier/$', cashier.cashier, name='artshow-cashier'),
    url(r'^cashier/bidder/(?P<bidder_id>\d+)/$', cashier.cashier_bidder,
        name='artshow-cashier-bidder'),
    url(r'^cashier/bidder/(?P<bidder_id>\d+)/invoices/$',
        cashier.cashier_bidder_invoices,
        name='artshow-cashier-bidder-invoices'),
    url(r'^cashier/invoice/(?P<invoice_id>\d+)/$', cashier.cashier_invoice,
        name='artshow-cashier-invoice'),
    url(r'^cashier/invoice/(?P<invoice_id>\d+)/print/$',
        cashier.cashier_print_invoice, name='artshow-print-invoice'),
    url(r'^cashier/invoice/(?P<invoice_id>\d+)/pdf/$', pdfreports.pdf_invoice),
    url(r'^cashier/invoice/(?P<invoice_id>\d+)/picklist/$',
        pdfreports.pdf_picklist),
    url(r'^reports/winning-bidders-pdf/$', pdfreports.winning_bidders,
        name='artshow-winning-bidders-pdf'),
    url(r'^reports/bid-entry-by-location-pdf/$',
        pdfreports.bid_entry_by_location),
    url(r'^reports/artists-csv/$', csvreports.artists,
        name='artshow-artists-csv'),
    url(r'^reports/pieces-csv/$', csvreports.pieces,
        name='artshow-pieces-csv'),
    url(r'^reports/bidders-csv/$', csvreports.bidders,
        name='artshow-bidders-csv'),
    url(r'^reports/payments-csv/$', csvreports.payments,
        name='artshow-payments-csv'),
    url(r'^reports/cheques-csv/$', csvreports.cheques,
        name='artshow-cheques-csv'),
    url(r'^access/$', views.artist_self_access, name='artshow-artist-access'),
    url(r'^bidderreg/$', bidderreg.wizard_view,
        name='artshow-bidderreg-wizard'),
    url(r'^bidderreg/(?P<pk>\d+)/done/$', bidderreg.final,
        name='artshow-bidderreg-final'),
    url(r'^bidder/(?P<pk>\d+)/agreement/$', bidderreg.bidder_agreement,
        name='artshow-bidder-agreement'),
    url(r'^bidder/$', views.bidder_results),
    url(r'^workflows/$', workflows.index, name='artshow-workflows'),
    url(r'^workflows/printing/$', workflows.printing,
        name='artshow-workflow-printing'),
]
