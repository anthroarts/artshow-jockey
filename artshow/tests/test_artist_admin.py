from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.conf import settings
from django.test import TestCase

from ..admin import ArtistAdmin
from ..models import (
    Allocation, Artist, Bid, Bidder, BidderId, Payment, Piece, Space)
from peeps.models import Person


class MockRequest:
    pass


request = MockRequest()


class ArtistAdminTest(TestCase):
    fixtures = ['artshowpaymenttypes', 'artshowspaces']

    def setUp(self):
        site = AdminSite()
        self.admin = ArtistAdmin(Artist, site)

        person = Person()
        person.save()

        self.artist = Artist(person=person)
        self.artist.save()

        gp_space = Space.objects.get(shortname='GP')
        gp_allocation = Allocation(artist=self.artist,
                                   space=gp_space,
                                   requested=2,
                                   allocated=2)
        gp_allocation.save()

        gt_space = Space.objects.get(shortname='GT')
        gt_allocation = Allocation(artist=self.artist,
                                   space=gt_space,
                                   requested=1.5,
                                   allocated=1.5)
        gt_allocation.save()

        bidder = Bidder(person=person)
        bidder.save()

        bidderid = BidderId(id='0365327', bidder=bidder)
        bidderid.save()

        # Piece 1-1 has no bids.
        piece = Piece(artist=self.artist, pieceid=1, min_bid=5, buy_now=50,
                      status=Piece.StatusInShow)
        piece.save()

        # Piece 1-2 has 1 bid.
        piece = Piece(artist=self.artist, pieceid=2, min_bid=5, buy_now=50,
                      status=Piece.StatusInShow)
        piece.save()

        bid = Bid(bidder=bidder, piece=piece, amount=10)
        bid.save()

    def test_apply_space_fees(self):
        self.admin.apply_space_fees(request, Artist.objects.all())

        payment = Payment.objects.get(artist=self.artist)
        self.assertEqual(payment.amount, Decimal(-35))  # 2 * $10 + 1.5 * $10
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'GP:2.0, GT:1.5')

    def test_apply_winnings_and_commission(self):
        self.admin.apply_winnings_and_commission(request, Artist.objects.all())

        winnings = Payment.objects.get(
            artist=self.artist,
            payment_type__pk=settings.ARTSHOW_SALES_PK)
        self.assertEqual(winnings.amount, Decimal(10))
        self.assertEqual(winnings.description, '2 pieces, 1 with bid')

        commission = Payment.objects.get(
            artist=self.artist,
            payment_type__pk=settings.ARTSHOW_COMMISSION_PK)
        self.assertEqual(commission.amount, Decimal(-1))
        self.assertEqual(commission.description, '10.0% of sales')

    def test_create_cheques(self):
        # Don't apply space fees so that the payment is positive.
        self.admin.apply_winnings_and_commission(request, Artist.objects.all())
        self.admin.create_cheques(request, Artist.objects.all())

        cheque = Payment.objects.get(
            artist=self.artist,
            payment_type__pk=settings.ARTSHOW_PAYMENT_SENT_PK)
        self.assertEqual(cheque.amount, Decimal(-9))
