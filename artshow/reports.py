# Artshow Jockey
# Copyright (C) 2009, 2010 Chris Cogdon
# See file COPYING for licence details
from decimal import Decimal
from django.shortcuts import render
from django.db.models import (
    Count, Exists, Max, OuterRef, Q, Subquery, Sum, Value as V
)
from django.db.models.fields import DecimalField
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import permission_required
from .models import (
    Allocation, Artist, Bid, BidderId, Invoice, InvoiceItem, InvoicePayment,
    Location, PaymentType, Piece, Space
)


@permission_required('artshow.is_artshow_staff')
def index(request):
    return render(request, 'artshow/reports.html')


@permission_required('artshow.is_artshow_staff')
def artists(request):
    query = request.GET.get('q', 'all')
    artists = Artist.objects.annotate(requested=Sum("allocation__requested"),
                                      allocated=Sum("allocation__allocated"))
    artists = list(artists)
    artists.sort(key=lambda x: x.artistname().lower())
    return render(request, 'artshow/reports-artists.html', {'artists': artists, 'query': query})


@permission_required('artshow.is_artshow_staff')
def winning_bidders(request):
    bidder_ids = BidderId.objects.filter(
        bidder__isnull=False
    ).order_by('bidder', 'id')
    winning_bid_query = Bid.objects.filter(
        piece=OuterRef('pk'), invalid=False).order_by('-amount')
    pieces = Piece.objects.values(
        'code', 'name', 'artist__publicname', 'artist__person__name',
        'voice_auction'
    ).filter(Exists(winning_bid_query)).annotate(
        winning_bidder=Subquery(winning_bid_query.values('bidder')[:1]),
        winning_bid=Subquery(winning_bid_query.values('amount')[:1])
    ).order_by('winning_bidder', 'artist', 'pieceid')

    bidders = []
    last_bidder = None
    for bidder_id in bidder_ids:
        if last_bidder != bidder_id.bidder_id:
            bidders.append({
                'bidder': bidder_id.bidder_id,
                'bidder_ids': [bidder_id.id],
                'pieces': [],
            })
            last_bidder = bidder_id.bidder_id
        else:
            bidders[-1]['bidder_ids'].append(bidder_id.id)

    bidder_index = 0
    for piece in pieces:
        assert piece['winning_bidder'] >= bidders[bidder_index]['bidder']
        while piece['winning_bidder'] != bidders[bidder_index]['bidder']:
            bidder_index += 1
        bidders[bidder_index]['pieces'].append(piece)

    bidders.sort(key=lambda bidder: bidder['bidder_ids'][0])

    return render(request, 'artshow/reports-winning-bidders.html',
                  {'bidders': bidders})


@permission_required('artshow.is_artshow_staff')
def unsold_pieces(request):
    winning_bid_query = Bid.objects.filter(
        piece=OuterRef('pk'), invalid=False).order_by('-amount')
    pieces = Piece.objects.values(
        'code', 'name', 'artist__publicname', 'artist__person__name',
        'voice_auction'
    ).filter(status=Piece.StatusWon).filter(
        Exists(winning_bid_query)
    ).annotate(
        winning_bidder=Subquery(winning_bid_query.values('bidder')[:1]),
        winning_bidder_name=Subquery(
            winning_bid_query.values('bidder__person__name')[:1]),
        winning_bidder_phone=Subquery(
            winning_bid_query.values('bidder__person__phone')[:1]),
        winning_bidder_email=Subquery(
            winning_bid_query.values('bidder__person__email')[:1]),
        winning_bid=Subquery(winning_bid_query.values('amount')[:1])
    ).order_by('winning_bidder', 'artist', 'pieceid')

    bidders = []
    last_bidder = None
    for piece in pieces:
        if last_bidder != piece['winning_bidder']:
            bidders.append({
                'id': piece['winning_bidder'],
                'name': piece['winning_bidder_name'],
                'phone': piece['winning_bidder_phone'],
                'email': piece['winning_bidder_email'],
                'pieces': [piece],
            })
            last_bidder = piece['winning_bidder']
        else:
            bidders[-1]['pieces'].append(piece)

    return render(request, 'artshow/reports-unsold-pieces.html',
                  {'bidders': bidders})


@permission_required('artshow.is_artshow_staff')
def artist_piece_report(request, artist_id):
    artist = Artist.objects.get(id=artist_id)
    pieces = artist.piece_set.all()
    return render(request, 'artshow/artist-piece-report.html', {'artist': artist, 'pieces': pieces})


@permission_required('artshow.is_artshow_staff')
def artist_panel_report(request):
    artists = list(Artist.objects.order_by('artistid'))
    for artist in artists:
        artist.locations = []

    artist_map = {artist.artistid: artist for artist in artists}
    for location in Location.objects.sorted().filter(Q(artist_1__isnull=False) | Q(artist_2__isnull=False)):
        if location.artist_1:
            artist_map[location.artist_1.artistid].locations.append(location.name)
        if location.artist_2:
            artist_map[location.artist_2.artistid].locations.append(location.name)
    return render(request, 'artshow/artist-panel-report.html', {'artists': artists})


@permission_required('artshow.is_artshow_staff')
def panel_artist_report(request):
    locations = Piece.objects.exclude(location="").values("location").distinct().order_by('location')
    for l in locations:
        l['artists'] = Artist.objects.filter(piece__location=l['location']) \
            .annotate(num_pieces=Count("artistid")) \
            .order_by("artistid")
    return render(request, "artshow/panel-artist-report.html", {
        'assigned_locations': Location.objects.sorted(),
        'locations': locations
    })


@permission_required('artshow.is_artshow_staff')
def artist_payment_report(request):
    non_zero = request.GET.get('nonzero', '0') == '1'
    artists = Artist.objects.annotate(total=Sum('payment__amount')).order_by("artistid")
    # TODO clean this up if/when we change the way "pending fees" are included in accounting.
    artists = list(artists)
    for a in artists:
        a.total = a.total or 0
        a.total_requested_cost, a.deduction_to_date, a.deduction_remaining = a.deduction_remaining_with_details()
        a.total -= a.deduction_remaining
    if non_zero:
        artists = [a for a in artists if a.total != 0]
    return render(request, 'artshow/artist-payment-report.html', {'artists': artists, 'non_zero': non_zero})


def get_summary_statistics():
    max_valid_bid = Max('bid__amount', filter=Q(bid__invalid=False))
    has_bid = Q(top_bid__isnull=False)
    general_rating = Q(adult=False)
    adult_rating = Q(adult=True)
    piece_showing = ~Q(status__in=[Piece.StatusNotInShow, Piece.StatusNotInShowLocked])
    voice_auction = Q(voice_auction=True)
    silent_auction = Q(voice_auction=False)

    piece_stats = Piece.objects.annotate(top_bid=max_valid_bid).aggregate(
        pieces_entered_all=Count('pk'),
        pieces_entered_general=Count('pk', filter=general_rating),
        pieces_entered_adult=Count('pk', filter=adult_rating),
        pieces_showing_all=Count('pk', filter=piece_showing),
        pieces_showing_general=Count('pk', filter=piece_showing & general_rating),
        pieces_showing_adult=Count('pk', filter=piece_showing & adult_rating),
        bids_all=Count('pk', filter=has_bid),
        bids_general=Count('pk', filter=has_bid & general_rating),
        bids_adult=Count('pk', filter=has_bid & adult_rating),
        pieces_va_all=Count('pk', filter=voice_auction),
        pieces_va_general=Count('pk', filter=voice_auction & general_rating),
        pieces_va_adult=Count('pk', filter=voice_auction & adult_rating),
        bidamt_all=Sum('top_bid'),
        bidamt_general=Sum('top_bid', filter=general_rating),
        bidamt_adult=Sum('top_bid', filter=adult_rating),
        bidamt_va_all=Sum('top_bid', filter=voice_auction),
        bidamt_va_general=Sum('top_bid', filter=voice_auction & general_rating),
        bidamt_va_adult=Sum('top_bid', filter=voice_auction & adult_rating),
        highest_amt_all=Max('top_bid'),
        highest_amt_general=Max('top_bid', filter=general_rating),
        highest_amt_adult=Max('top_bid', filter=adult_rating),
        highest_amt_va_all=Max('top_bid', filter=voice_auction),
        highest_amt_va_general=Max('top_bid', filter=voice_auction & general_rating),
        highest_amt_va_adult=Max('top_bid', filter=voice_auction & adult_rating),
        highest_amt_sa_all=Max('top_bid', filter=silent_auction),
        highest_amt_sa_general=Max('top_bid', filter=silent_auction & general_rating),
        highest_amt_sa_adult=Max('top_bid', filter=silent_auction & adult_rating),
    )

    artist_stats = Artist.objects.annotate(
        num_requested=Sum('allocation__requested'),
        num_allocated=Sum('allocation__allocated')).aggregate(
        count=Count('pk'),
        count_active=Count('pk', filter=Q(num_requested__gt=0)),
        count_showing=Count('pk', filter=Q(num_allocated__gt=0))
    )

    decimal_zero = V(0, output_field=DecimalField())

    payment_types = PaymentType.objects.annotate(
        total_payments=Coalesce(Sum('payment__amount'), decimal_zero))
    total_payments = sum([pt.total_payments for pt in payment_types])

    tax_paid = Invoice.objects.aggregate(tax_paid=Sum('tax_paid'))['tax_paid'] or Decimal(0)
    piece_charges = InvoiceItem.objects.aggregate(piece_charges=Sum('price'))['piece_charges'] or Decimal(0)
    total_charges = tax_paid + piece_charges

    invoice_payments = InvoicePayment.objects.values('payment_method').annotate(total=Sum('amount'))
    payment_method_choice_dict = dict(InvoicePayment.PAYMENT_METHOD_CHOICES)
    total_invoice_payments = Decimal(0)
    for ip in invoice_payments:
        ip['payment_method_desc'] = payment_method_choice_dict[ip['payment_method']]
        total_invoice_payments += ip['total']

    spaces = Space.objects.annotate(
        requested=Coalesce(Sum('allocation__requested'), decimal_zero),
        allocated2=Coalesce(Sum('allocation__allocated'), decimal_zero))
    total_spaces = {
        'available': 0,
        'requested': 0,
        'allocated': 0,
        'requested_perc': 0,
        'allocated_perc': 0
    }
    for s in spaces:
        total_spaces['available'] += s.available
        total_spaces['requested'] += s.requested
        total_spaces['allocated'] += s.allocated2
        if s.available:
            s.requested_perc = s.requested / s.available * 100
            s.allocated_perc = s.allocated2 / s.available * 100
        else:
            s.requested_perc = 0
            s.allocated_perc = 0
    if total_spaces['available']:
        total_spaces['requested_perc'] = \
            total_spaces['requested'] / total_spaces['available'] * 100
        total_spaces['allocated_perc'] = \
            total_spaces['allocated'] / total_spaces['available'] * 100

    # all_invoices = Invoice.objects.aggregate ( Sum('tax_paid'), Sum('invoicepayment__amount') )

    return {
        'piece_stats': piece_stats,
        'artist_stats': artist_stats,
        'payment_types': payment_types,
        'total_payments': total_payments,
        'tax_paid': tax_paid,
        'piece_charges': piece_charges,
        'total_charges': total_charges,
        'total_invoice_payments': total_invoice_payments,
        'invoice_payments': invoice_payments,
        'spaces': spaces,
        'total_spaces': total_spaces,
    }


@permission_required('artshow.is_artshow_staff')
def show_summary(request):

    statistics = get_summary_statistics()
    format = request.GET.get("format")

    if format == "json":
        pass
    else:
        return render(request, 'artshow/show-summary.html', statistics)


@permission_required('artshow.is_artshow_staff')
def allocations_waiting(request):
    short_allocations = {}
    over_allocations = {}

    for space in Space.objects.all():
        subquery = Allocation.objects \
            .filter(artist=OuterRef('artistid'), space=space) \
            .annotate(total_requested=Sum('requested')) \
            .values('total_requested')
        artists = {
            artist.artistid: artist
            for artist in Artist.objects.annotate(requested=Subquery(subquery))
        }

        for artist in artists.values():
            if artist.requested is None:
                artist.requested = 0.0
            artist.allocated = 0.0

        for location in Location.objects.filter(type=space):
            size = 1.0
            if location.half_space or location.half_free or (location.artist_1 and location.artist_2):
                size = 0.5
            if location.artist_1:
                artists[location.artist_1.artistid].allocated += size
            if location.artist_2:
                artists[location.artist_2.artistid].allocated += size

        for artist in artists.values():
            map = None
            if artist.allocated > artist.requested:
                map = over_allocations
            elif artist.allocated < artist.requested:
                map = short_allocations
            else:
                continue

            space_artists = map.setdefault(space.name, [])
            space_artists.append({
                'artistid': artist.artistid,
                'artist': str(artist),
                'requested': artist.requested,
                'allocated': artist.allocated,
            })

    sections = [
        ('Short Allocations', short_allocations),
        ('Over Allocations', over_allocations),
    ]

    return render(request, 'artshow/allocations_waiting.html', {'sections': sections})


@permission_required('artshow.is_artshow_staff')
def voice_auction(request):
    adult = request.GET.get('adult', '')
    if adult not in ['y', 'n']:
        adult = ''

    pieces = Piece.objects.exclude(status=Piece.StatusNotInShow).filter(voice_auction=True).order_by("order", "artist",
                                                                                                     "pieceid")
    if adult == "y":
        pieces = pieces.filter(adult=True)
    elif adult == "n":
        pieces = pieces.filter(adult=False)

    return render(request, 'artshow/voice-auction.html', {'pieces': pieces, 'adult': adult})


@permission_required('artshow.is_artshow_staff')
def sales_percentiles(request):
    groups = int(request.GET.get('groups', '20'))

    amounts = []
    perc_amounts = []
    pieces = Piece.objects.exclude(status=Piece.StatusNotInShow)
    for p in pieces:
        try:
            tb = p.top_bid()
            amounts.append(tb.amount)
        except Bid.DoesNotExist:
            pass

    if amounts:
        amounts.sort()
        num_amounts = len(amounts)
        groups = min(groups, num_amounts)

        for i in range(1, groups):
            j = float(i) * num_amounts / groups
            j_before = int(j)
            j_after = j_before + 1
            amount = float(amounts[j_before]) * (j_after - j) + float(amounts[j_after]) * (j - j_before)
            perc_amounts.append({'perc': float(i) / groups, 'amount': amount})
        perc_amounts.append({'perc': 1.0, 'amount': float(amounts[-1])})

    return render(request, 'artshow/sales-percentiles.html', {'perc_amounts': perc_amounts})
