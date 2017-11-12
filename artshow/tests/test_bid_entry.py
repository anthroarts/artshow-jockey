from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase

from peeps.models import Person

from ..models import Artist, Bid, Bidder, BidderId, Piece


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
        piece = Piece(artist=artist, pieceid=1)
        piece.save()

        # Piece 1-2 has 2 bids.
        piece = Piece(artist=artist, pieceid=2)
        piece.save()

        bid = Bid(bidder=bidder, piece=piece, amount=10)
        bid.save()

        bid = Bid(bidder=bidder, piece=piece, amount=15, buy_now_bid=True)
        bid.save()

        self.client = Client()
        self.client.login(username='test', password='test')

    def tearDown(self):
        self.user.delete()

    def test_invalid_artist(self):
        response = self.client.get('/artshow/entry/bids/2/1/')
        self.assertEquals('artist_id', response.json()['error']['field'])

    def test_invalid_piece(self):
        response = self.client.get('/artshow/entry/bids/1/3/')
        self.assertEquals('piece_id', response.json()['error']['field'])

    def test_piece_no_bids(self):
        response = self.client.get('/artshow/entry/bids/1/1/')
        self.assertEquals([], response.json()['bids'])

    def test_piece_two_bids(self):
        response = self.client.get('/artshow/entry/bids/1/2/')
        expected_bids = [
            {'bidder': '0365327',
             'bid': 10,
             'buy_now_bid': False},
            {'bidder': '0365327',
             'bid': 15,
             'buy_now_bid': True},
        ]
        self.assertEquals(expected_bids, response.json()['bids'])
