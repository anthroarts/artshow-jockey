from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
import json

from ..models import Artist, Bid, Bidder, BidderId, Piece
from peeps.models import Person


class BidEntryTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
                username='test', email='test@example.com', password='test')
        permission = Permission.objects.get(codename='add_bid')
        self.user.user_permissions.add(permission)
        self.user.save()

        person = Person()
        person.save()

        artist = Artist(person=person)
        artist.save()

        bidder = Bidder(person=person)
        bidder.save()

        bidderid = BidderId(id='0365327', bidder=bidder)
        bidderid.save()

        # Piece 1-1 has no bids.
        piece = Piece(artist=artist, pieceid=1, min_bid=5, buy_now=50,
                      status=Piece.StatusInShow)
        piece.save()

        # Piece 1-2 has 2 bids.
        piece = Piece(artist=artist, pieceid=2, min_bid=5, buy_now=50,
                      status=Piece.StatusInShow)
        piece.save()

        bid = Bid(bidder=bidder, piece=piece, amount=10)
        bid.save()

        bid = Bid(bidder=bidder, piece=piece, amount=20)
        bid.save()

        self.client = Client()
        self.client.login(username='test', password='test')

    def postJson(self, path, data):
        return self.client.post(path, data=json.dumps(data),
                                content_type='application/json')

    def test_invalid_artist(self):
        response = self.client.get('/artshow/entry/bids/2/1/')
        expected = {
            'error': {
                'field': 'artist_id',
                'message': 'Invalid artist ID',
            }
        }
        self.assertEquals(response.json(), expected)

    def test_invalid_piece(self):
        response = self.client.get('/artshow/entry/bids/1/3/')
        expected = {
            'error': {
                'field': 'piece_id',
                'message': 'Invalid piece ID',
            }
        }
        self.assertEquals(response.json(), expected)

    def test_piece_no_bids(self):
        response = self.client.get('/artshow/entry/bids/1/1/')
        expected = {'bids': []}
        self.assertEquals(response.json(), expected)

    def test_piece_two_bids(self):
        response = self.client.get('/artshow/entry/bids/1/2/')
        expected = {
            'bids': [
                {'bidder': '0365327',
                 'bid': 10,
                 'buy_now_bid': False},
                {'bidder': '0365327',
                 'bid': 20,
                 'buy_now_bid': False},
            ]
        }
        self.assertEquals(response.json(), expected)

    def test_invalid_bidder(self):
        bids = [
            {'bidder': '0365327',
             'bid': 10,
             'buy_now_bid': False},
            {'bidder': '0123456',
             'bid': 10,
             'buy_now_bid': False},
        ]
        response = self.postJson('/artshow/entry/bids/1/1/',
                                 {'bids': bids})
        expected = {
            'error': {
                'field': 'bidder',
                'index': 1,
                'message': 'Invalid bidder ID',
            }
        }
        self.assertEquals(response.json(), expected)

    def test_add_bids(self):
        expected = {
            'bids': [
                {'bidder': '0365327',
                 'bid': 5,
                 'buy_now_bid': False},
                {'bidder': '0365327',
                 'bid': 10,
                 'buy_now_bid': False},
            ]
        }
        response = self.postJson('/artshow/entry/bids/1/1/', expected)
        self.assertEquals(response.json(), expected)

    def test_replace_bids(self):
        expected = {
            'bids': [
                {'bidder': '0365327',
                 'bid': 50,
                 'buy_now_bid': True},
            ]
        }
        response = self.postJson('/artshow/entry/bids/1/2/', expected)
        self.assertEquals(response.json(), expected)

    def test_piece_cannot_buy_now(self):
        bids = [
            {'bidder': '0365327',
             'bid': 10,
             'buy_now_bid': False},
            {'bidder': '0365327',
             'bid': 50,
             'buy_now_bid': True},
        ]
        response = self.postJson('/artshow/entry/bids/1/2/', {'bids': bids})
        expected = {
            'error': {
                'field': 'bid',
                'index': 1,
                'message': 'Buy Now option not available on piece with bids',
            }
        }
        self.assertEquals(response.json(), expected)

        # Original bids should be unchanged.
        response = self.client.get('/artshow/entry/bids/1/2/')
        expected = {
            'bids': [
                {'bidder': '0365327',
                 'bid': 10,
                 'buy_now_bid': False},
                {'bidder': '0365327',
                 'bid': 20,
                 'buy_now_bid': False},
            ]
        }
        self.assertEquals(response.json(), expected)

    def test_non_monotonic_bids(self):
        bids = [
            {'bidder': '0365327',
             'bid': 20,
             'buy_now_bid': False},
            {'bidder': '0365327',
             'bid': 10,
             'buy_now_bid': False},
        ]
        response = self.postJson('/artshow/entry/bids/1/2/', {'bids': bids})
        expected = {
            'error': {
                'field': 'bid',
                'index': 1,
                'message': 'New bid must be higher than existing bids',
            }
        }
        self.assertEquals(response.json(), expected)

        # Original bids should be unchanged.
        response = self.client.get('/artshow/entry/bids/1/2/')
        expected = {
            'bids': [
                {'bidder': '0365327',
                 'bid': 10,
                 'buy_now_bid': False},
                {'bidder': '0365327',
                 'bid': 20,
                 'buy_now_bid': False},
            ]
        }
        self.assertEquals(response.json(), expected)

