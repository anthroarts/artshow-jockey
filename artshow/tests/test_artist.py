from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse

from ..admin import ArtistAdmin
from ..models import (
    Allocation, Artist, Bid, Bidder, BidderId, Payment, Piece, Space)
from peeps.models import Person


class MockRequest:
    pass


class ArtistTest(TestCase):
    fixtures = ['artshowpaymenttypes', 'artshowspaces']

    def setUp(self):
        person = Person()
        person.save()

        self.artist_1 = Artist(person=person)
        self.artist_1.save()

        person = Person()
        person.save()

        self.artist_2 = Artist(person=person)
        self.artist_2.save()

        allocation = Allocation(artist=self.artist_1,
                                space=Space.objects.get(shortname='GP'),
                                requested=2,
                                allocated=2)
        allocation.save()

        allocation = Allocation(artist=self.artist_1,
                                space=Space.objects.get(shortname='GT'),
                                requested=1.5,
                                allocated=1.5)
        allocation.save()

        allocation = Allocation(artist=self.artist_2,
                                space=Space.objects.get(shortname='AP'),
                                requested=3,
                                allocated=3)
        allocation.save()

        allocation = Allocation(artist=self.artist_2,
                                space=Space.objects.get(shortname='AT'),
                                requested=1.5,
                                allocated=1)  # Half-table unallocated
        allocation.save()

        person = Person()
        person.save()

        bidder = Bidder(person=person)
        bidder.save()

        bidderid = BidderId(id='0365327', bidder=bidder)
        bidderid.save()

        # Piece 1-1 has no bids.
        piece = Piece(artist=self.artist_1, pieceid=1, min_bid=5, buy_now=50,
                      status=Piece.StatusInShow, location='A1')
        piece.save()

        # Piece 1-2 has a $10 bid.
        piece = Piece(artist=self.artist_1, pieceid=2, min_bid=5, buy_now=50,
                      status=Piece.StatusInShow, location='A1')
        piece.save()

        bid = Bid(bidder=bidder, piece=piece, amount=10)
        bid.save()

        # Piece 2-1 has no bids.
        piece = Piece(artist=self.artist_2, pieceid=1, min_bid=5, buy_now=50,
                      status=Piece.StatusInShow, location='B1')
        piece.save()

        # Piece 2-2 has a $20 bid.
        piece = Piece(artist=self.artist_2, pieceid=2, min_bid=5, buy_now=50,
                      status=Piece.StatusInShow, location='B1')
        piece.save()

        bid = Bid(bidder=bidder, piece=piece, amount=20)
        bid.save()

    def test_apply_space_fees(self):
        Artist.apply_space_fees(Artist.objects.all())

        self.assertEqual(Payment.objects.count(), 2)

        payment = Payment.objects.get(
            artist=self.artist_1,
            payment_type_id=settings.ARTSHOW_SPACE_FEE_PK)
        self.assertEqual(payment.amount, Decimal(-35))  # 2 * $10 + 1.5 * $10
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'GP:2.0, GT:1.5')

        payment = Payment.objects.get(
            artist=self.artist_2,
            payment_type_id=settings.ARTSHOW_SPACE_FEE_PK)
        payment = Payment.objects.get(artist=self.artist_2)
        self.assertEqual(payment.amount, Decimal(-40))  # 3 * $10 + 1 * $10
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'AP:3.0, AT:1.0')

    def test_apply_winnings_and_commission(self):
        Artist.apply_winnings_and_commission(Artist.objects.all())

        self.assertEqual(Payment.objects.count(), 4)

        winnings = Payment.objects.get(
            artist=self.artist_1,
            payment_type_id=settings.ARTSHOW_SALES_PK)
        self.assertEqual(winnings.amount, Decimal(10))
        self.assertEqual(winnings.description, '2 pieces, 1 with bid')

        commission = Payment.objects.get(
            artist=self.artist_1,
            payment_type_id=settings.ARTSHOW_COMMISSION_PK)
        self.assertEqual(commission.amount, Decimal(-1))
        self.assertEqual(commission.description, '10.0% of sales')

        winnings = Payment.objects.get(
            artist=self.artist_2,
            payment_type_id=settings.ARTSHOW_SALES_PK)
        self.assertEqual(winnings.amount, Decimal(20))
        self.assertEqual(winnings.description, '2 pieces, 1 with bid')

        commission = Payment.objects.get(
            artist=self.artist_2,
            payment_type_id=settings.ARTSHOW_COMMISSION_PK)
        self.assertEqual(commission.amount, Decimal(-2))
        self.assertEqual(commission.description, '10.0% of sales')

    def test_create_cheques(self):
        site = AdminSite()
        admin = ArtistAdmin(Artist, site)
        request = MockRequest()

        # Don't apply space fees so that the payment is positive.
        Artist.apply_winnings_and_commission(Artist.objects.all())
        admin.create_cheques(request, Artist.objects.all())

        self.assertEqual(Payment.objects.count(), 6)

        cheque = Payment.objects.get(
            artist=self.artist_1,
            payment_type_id=settings.ARTSHOW_PAYMENT_SENT_PK)
        self.assertEqual(cheque.amount, Decimal(-9))

        cheque = Payment.objects.get(
            artist=self.artist_2,
            payment_type_id=settings.ARTSHOW_PAYMENT_SENT_PK)
        self.assertEqual(cheque.amount, Decimal(-18))

    def test_close_show(self):
        user = User.objects.create_user(
            username='test', email='test@example.com', password='test')
        permission = Permission.objects.get(codename='is_artshow_staff')
        user.user_permissions.add(permission)
        user.save()

        c = Client()
        c.login(username='test', password='test')
        response = c.get(reverse('artshow-workflow-close-show'))
        self.assertEqual(response.status_code, 200)

        response = c.post(reverse('artshow-workflow-close-show'))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Payment.objects.count(), 6)

        payment = Payment.objects.get(
            artist=self.artist_1,
            payment_type_id=settings.ARTSHOW_SPACE_FEE_PK)
        self.assertEqual(payment.amount, Decimal(-35))  # 2 * $10 + 1.5 * $10
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'GP:2.0, GT:1.5')

        winnings = Payment.objects.get(
            artist=self.artist_1,
            payment_type_id=settings.ARTSHOW_SALES_PK)
        self.assertEqual(winnings.amount, Decimal(10))
        self.assertEqual(winnings.description, '2 pieces, 1 with bid')

        commission = Payment.objects.get(
            artist=self.artist_1,
            payment_type_id=settings.ARTSHOW_COMMISSION_PK)
        self.assertEqual(commission.amount, Decimal(-1))
        self.assertEqual(commission.description, '10.0% of sales')

        payment = Payment.objects.get(
            artist=self.artist_2,
            payment_type_id=settings.ARTSHOW_SPACE_FEE_PK)
        self.assertEqual(payment.amount, Decimal(-40))  # 3 * $10 + 1 * $10
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'AP:3.0, AT:1.0')

        winnings = Payment.objects.get(
            artist=self.artist_2,
            payment_type_id=settings.ARTSHOW_SALES_PK)
        self.assertEqual(winnings.amount, Decimal(20))
        self.assertEqual(winnings.description, '2 pieces, 1 with bid')

        commission = Payment.objects.get(
            artist=self.artist_2,
            payment_type_id=settings.ARTSHOW_COMMISSION_PK)
        self.assertEqual(commission.amount, Decimal(-2))
        self.assertEqual(commission.description, '10.0% of sales')
