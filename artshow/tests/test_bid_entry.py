from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
import json

from ..models import Artist, Bid, Bidder, BidderId, Location, Piece, Space
from peeps.models import Person


class BidEntryTests(TestCase):
    fixtures = ['artshowpaymenttypes', 'artshowspaces']

    def setUp(self):
        self.user = User.objects.create_user(
            username='test', email='test@example.com', password='test')
        permission = Permission.objects.get(codename='is_artshow_staff')
        self.user.user_permissions.add(permission)
        self.user.save()

        person = Person()
        person.save()

        artist = Artist(person=person)
        artist.save()

        gp = Space.objects.get(shortname='GP')

        Location.objects.bulk_create([
            Location(name='A1', type=gp, artist_1=artist),
            Location(name='A2', type=gp, artist_2=artist),
            Location(name='A3', type=gp),
        ])

        bidder = Bidder(person=person)
        bidder.save()

        bidderid = BidderId(id='0365327', bidder=bidder)
        bidderid.save()

        unassigned_bidderid = BidderId(id='0019')
        unassigned_bidderid.save()

        # Piece 1-1 has no bids and is not marked in show yet.
        piece = Piece(artist=artist, pieceid=1, min_bid=5, buy_now=50)
        piece.save()

        # Piece 1-2 has 2 bids and is already in the show.
        piece = Piece(artist=artist, pieceid=2, min_bid=5, buy_now=50,
                      status=Piece.StatusInShow,
                      location='A1')
        piece.save()

        bid = Bid(bidder=bidder, piece=piece, amount=10)
        bid.save()

        bid = Bid(bidder=bidder, piece=piece, amount=20)
        bid.save()

        # Piece 1-3 has no buy now price.
        piece = Piece(artist=artist, pieceid=3, min_bid=5,
                      status=Piece.StatusInShow,
                      location='A2')
        piece.save()

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
        self.assertEqual(response.json(), expected)

    def test_invalid_piece(self):
        response = self.client.get('/artshow/entry/bids/1/4/')
        expected = {
            'error': {
                'field': 'piece_id',
                'message': 'Invalid piece ID',
            }
        }
        self.assertEqual(response.json(), expected)

    def test_piece_no_bids(self):
        response = self.client.get('/artshow/entry/bids/1/1/')
        self.assertEqual(response.json(), {
            'bids': [],
            'buy_now': 50,
            'last_updated': None,
            'location': '',
            'locations': ['A1', 'A2'],
        })

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
            ],
            'buy_now': 50,
            'last_updated': None,
            'location': 'A1',
            'locations': ['A1', 'A2'],
        }
        self.assertEqual(response.json(), expected)

    def test_piece_no_buy_now(self):
        response = self.client.get('/artshow/entry/bids/1/3/')
        expected = {
            'bids': [],
            'buy_now': None,
            'last_updated': None,
            'location': 'A2',
            'locations': ['A1', 'A2'],
        }
        self.assertEqual(response.json(), expected)

    def test_invalid_bidder(self):
        data = {
            'bids': [
                {'bidder': '0365327',
                 'bid': 10,
                 'buy_now_bid': False},
                {'bidder': '0123456',
                 'bid': 10,
                 'buy_now_bid': False},
            ],
            'location': 'A1',
        }
        response = self.postJson('/artshow/entry/bids/1/1/', data)
        expected = {
            'error': {
                'field': 'bidder',
                'index': 1,
                'message': 'Invalid bidder ID',
            }
        }
        self.assertEqual(response.json(), expected)

    def test_unassigned_bidder_id(self):
        data = {
            'bids': [
                {'bidder': '0019',
                 'bid': 10,
                 'buy_now_bid': False},
            ],
            'location': 'A1',
        }
        response = self.postJson('/artshow/entry/bids/1/1/', data)
        expected = {
            'error': {
                'field': 'bidder',
                'index': 0,
                'message': 'Unassigned bidder ID',
            }
        }
        self.assertEqual(response.json(), expected)

    def test_add_bids(self):
        expected = {
            'bids': [
                {'bidder': '0365327',
                 'bid': 5,
                 'buy_now_bid': False},
                {'bidder': '0365327',
                 'bid': 10,
                 'buy_now_bid': False},
            ],
            'location': 'a1',
        }
        response = self.postJson('/artshow/entry/bids/1/1/', expected)
        self.assertEqual(response.json()['bids'], expected['bids'])
        self.assertEqual(response.json()['location'], 'A1')  # 'a1' upper cased
        self.assertIsNotNone(response.json()['last_updated'])

    def test_replace_bids(self):
        expected = {
            'bids': [
                {'bidder': '0365327',
                 'bid': 50,
                 'buy_now_bid': True},
            ],
            'location': 'A1',
        }
        response = self.postJson('/artshow/entry/bids/1/2/', expected)
        self.assertEqual(response.json()['bids'], expected['bids'])
        self.assertEqual(response.json()['location'], expected['location'])
        self.assertIsNotNone(response.json()['last_updated'])

    def test_piece_cannot_buy_now(self):
        data = {
            'bids': [
                {'bidder': '0365327',
                 'bid': 10,
                 'buy_now_bid': False},
                {'bidder': '0365327',
                 'bid': 50,
                 'buy_now_bid': True},
            ],
            'location': 'A1',
        }
        response = self.postJson('/artshow/entry/bids/1/2/', data)
        expected = {
            'error': {
                'field': 'bid',
                'index': 1,
                'message': 'Buy Now option not available on piece with bids',
            }
        }
        self.assertEqual(response.json(), expected)

        # Original bids should be unchanged.
        response = self.client.get('/artshow/entry/bids/1/2/')
        expected = [
            {'bidder': '0365327',
             'bid': 10,
             'buy_now_bid': False},
            {'bidder': '0365327',
             'bid': 20,
             'buy_now_bid': False},
        ]
        self.assertEqual(response.json()['bids'], expected)

    def test_non_monotonic_bids(self):
        data = {
            'bids': [
                {'bidder': '0365327',
                 'bid': 20,
                 'buy_now_bid': False},
                {'bidder': '0365327',
                 'bid': 10,
                 'buy_now_bid': False},
            ],
            'location': 'A1',
        }
        response = self.postJson('/artshow/entry/bids/1/2/', data)
        expected = {
            'error': {
                'field': 'bid',
                'index': 1,
                'message': 'New bid must be higher than existing bids',
            }
        }
        self.assertEqual(response.json(), expected)

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
            ],
            'buy_now': 50,
            'last_updated': None,
            'location': 'A1',
            'locations': ['A1', 'A2'],
        }
        self.assertEqual(response.json(), expected)
