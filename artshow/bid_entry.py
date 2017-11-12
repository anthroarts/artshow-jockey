from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
import json

from .models import Artist, Piece


def error_response(field, message):
    return JsonResponse({
        'error': {
            'field': field,
            'message': message,
        }
    })


@permission_required('artshow.add_bid')
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
        return set_bids(piece, json.loads(request.body))


def get_bids(piece):
    bids = piece.bid_set.exclude(invalid=True).order_by('amount')
    return JsonResponse({
        'bids': [{
            'bidder': bid.bidderid.id,
            'bid': float(bid.amount),
            'buy_now_bid': bid.buy_now_bid,
        } for bid in bids]
    })


def set_bids(piece, body):
    pass
