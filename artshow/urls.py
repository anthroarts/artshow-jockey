# Artshow Jockey
# Copyright (C) 2009, 2010 Chris Cogdon
# See file COPYING for licence details

from django.conf.urls import url
from django.contrib.auth.decorators import permission_required

from . import addbidder
from . import bidderreg
from . import cashier
from . import csvreports
from . import pdfreports
from . import reports
from . import views
from . import voice_auction
from . import workflows

urlpatterns = [
    url(r'^$', views.index),
    url(r'^entry/$', views.dataentry),
    url(r'^entry/bidders/$', addbidder.bulk_add),
    url(r'^entry/bids/$', addbidder.bid_bulk_add),
    url(r'^entry/auction_bids/(?P<adult>[yn])/$', voice_auction.auction_bids),
    url(r'^entry/order_auction/(?P<adult>[yn])/$', voice_auction.order_auction),
    #url(r'^entry/bids/location/(?P<location>[^/]+)/$', bidentry.add_bids),
    url(r'^reports/$', reports.index),
    url(r'^artist/(?P<artist_id>\d+)/mailinglabel/$', views.artist_mailing_label),
    url(r'^artist/(?P<artist_id>\d+)/piecereport/$', reports.artist_piece_report),
    url(r'^reports/artists/$', reports.artists),
    url(r'^reports/winning-bidders/$', reports.winning_bidders),
    url(r'^reports/artist-panel-report/$', reports.artist_panel_report),
    url(r'^reports/panel-artist-report/$', reports.panel_artist_report),
    url(r'^reports/artist-payment-report/$', reports.artist_payment_report),
    url(r'^reports/show-summary/$', reports.show_summary),
    url(r'^reports/voice-auction/$', reports.voice_auction),
    url(r'^reports/sales-percentiles/$', reports.sales_percentiles),
    url(r'^reports/allocations-waiting/$', reports.allocations_waiting),
    url(r'^cashier/$', cashier.cashier),
    url(r'^cashier/bidder/(?P<bidder_id>\d+)/$', cashier.cashier_bidder),
    url(r'^cashier/bidder/(?P<bidder_id>\d+)/invoices/$', cashier.cashier_bidder_invoices),
    url(r'^cashier/invoice/(?P<invoice_id>\d+)/$', cashier.cashier_invoice),
    url(r'^cashier/invoice/(?P<invoice_id>\d+)/print/$', cashier.print_invoice),
    url(r'^cashier/invoice/(?P<invoice_id>\d+)/pdf/$', pdfreports.pdf_invoice),
    url(r'^cashier/invoice/(?P<invoice_id>\d+)/picklist/$', pdfreports.pdf_picklist),
    url(r'^reports/winning-bidders-pdf/$', pdfreports.winning_bidders),
    url(r'^reports/bid-entry-by-location-pdf/$', pdfreports.bid_entry_by_location),
    url(r'^reports/artists-csv/$', csvreports.artists),
    url(r'^reports/pieces-csv/$', csvreports.pieces),
    url(r'^reports/bidders-csv/$', csvreports.bidders),
    url(r'^reports/payments-csv/$', csvreports.payments),
    url(r'^reports/cheques-csv/$', csvreports.cheques),
    url(r'^access/$', views.artist_self_access),
    url(r'^bidderreg/$', bidderreg.wizard_view, name="artshow-bidderreg-wizard"),
    url(r'^bidderreg/done/$', bidderreg.final),
    url(r'^bidder/$', views.bidder_results),
    url(r'^workflows/$', workflows.index),
    url(r'^workflows/printing/$', workflows.printing),
]
