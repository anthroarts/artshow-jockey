from decimal import Decimal
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
import json

from .models import Artist, Bid, BidderId, Piece


@permission_required('artshow.is_artshow_staff')
def bid_entry(request):
    return render(request, 'artshow/bid_entry.html',
                  {'bid_slots': list(range(1, 7))})


def error_response(field, message, index=None):
    error = {
        'field': field,
        'message': message,
    }
    if index is not None:
        error['index'] = index
    return JsonResponse({'error': error})


@permission_required('artshow.is_artshow_staff')
def bids(request, artist_id, piece_id):
    try:
        piece = Piece.objects.get(artist__artistid=artist_id,
                                  pieceid=piece_id)
    except Piece.DoesNotExist:
        try:
            Artist.objects.get(artistid=artist_id)
            return error_response('piece_id', 'Invalid piece ID')
        except Artist.DoesNotExist:
            return error_response('artist_id', 'Invalid artist ID')

    if request.method == 'GET':
        return get_bids(piece)
    elif request.method == 'POST':
        return set_bids(piece, json.loads(request.body.decode('utf-8')))


def get_bids(piece):
    bids = piece.bid_set.exclude(invalid=True).order_by('amount')

    bids_updated = None
    if piece.bids_updated:
        bids_updated = piece.bids_updated.isoformat()

    return JsonResponse({
        'bids': [{
            'bidder': bid.bidderid.id,
            'bid': float(bid.amount),
            'buy_now_bid': bid.buy_now_bid,
        } for bid in bids],
        'last_updated': bids_updated,
        'location': piece.location,
        'locations': piece.artist.assigned_locations(),
        'buy_now': None if piece.buy_now is None else float(piece.buy_now),
    })


def set_bids(piece, data):
    existing_bids = piece.bid_set.exclude(invalid=True).order_by('amount')

    try:
        with transaction.atomic():
            # Update piece first so that it is marked as InShow.
            piece.bids_updated = timezone.now()
            piece.location = data['location'].upper()
            piece.save()

            bids = data['bids']
            for i in range(len(bids)):
                try:
                    bidderid = BidderId.objects.get(id=bids[i]['bidder'])
                except BidderId.DoesNotExist:
                    return error_response('bidder', 'Invalid bidder ID', i)

                if not bidderid.bidder:
                    return error_response('bidder', 'Unassigned bidder ID', i)

                amount = Decimal(bids[i]['bid'])
                buy_now_bid = bool(bids[i]['buy_now_bid'])

                if i < len(existing_bids):
                    # Skip this bid if it is unchanged. Otherwise delete it and
                    # all following bids so that the new set can be
                    # re-validated.
                    existing_bid = existing_bids[i]
                    if existing_bid.bidderid is bidderid and \
                       existing_bid.amount == amount and \
                       existing_bid.but_now_bid == buy_now_bid:
                        continue  # Next bid
                    else:
                        for j in range(i, len(existing_bids)):
                            existing_bids[j].delete()
                        existing_bids = existing_bids[:i]

                new_bid = Bid(piece=piece,
                              bidder=bidderid.bidder,
                              bidderid=bidderid,
                              amount=amount,
                              buy_now_bid=buy_now_bid)
                new_bid.validate()
                new_bid.save()

            # Handle bids that have been deleted.
            for i in range(len(bids), len(existing_bids)):
                existing_bids[i].delete()

        return get_bids(piece)
    except ValidationError as e:
        return error_response('bid', e.message, i)
