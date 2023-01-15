from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse

from ..models import (
    Allocation, Artist, Bid, Bidder, BidderId, Location, Payment, Piece, Space)
from peeps.models import Person


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

        person = Person()
        person.save()

        self.artist_3 = Artist(person=person)
        self.artist_3.save()

        person = Person()
        person.save()

        self.artist_4 = Artist(person=person)
        self.artist_4.save()

        gp = Space.objects.get(shortname='GP')
        gt = Space.objects.get(shortname='GT')
        ap = Space.objects.get(shortname='AP')
        at = Space.objects.get(shortname='AT')

        Allocation.objects.bulk_create([
            Allocation(artist=self.artist_1, space=gp, requested=2),
            Allocation(artist=self.artist_1, space=gt, requested=1.5),
            Allocation(artist=self.artist_2, space=ap, requested=3),
            Allocation(artist=self.artist_2, space=at, requested=1.5),
        ])

        Location.objects.bulk_create([
            Location(name='A1', type=gp, artist_1=self.artist_1),
            Location(name='A2', type=gp, artist_1=self.artist_1),
            Location(name='B1', type=gt, artist_1=self.artist_1),
            Location(name='B2', type=gt, artist_1=self.artist_1, space_is_split=True),
            # Use the "artist_2" slot for artist_2 for testing purposes.
            Location(name='X1', type=ap, artist_2=self.artist_2),
            Location(name='X2', type=ap, artist_2=self.artist_2),
            Location(name='X3', type=ap, artist_2=self.artist_2),
            Location(name='Y1', type=at, artist_2=self.artist_2),
            Location(name='Y2', type=at, half_space=True),  # Unallocated
            Location(name='C1', type=gp, artist_1=self.artist_4),
        ])

        pieces = [
            Piece(artist=self.artist_1, pieceid=1, min_bid=5, buy_now=50,
                  status=Piece.StatusInShow, location='A1'),
            Piece(artist=self.artist_2, pieceid=1, min_bid=5, buy_now=50,
                  status=Piece.StatusInShow, location='X1'),
            Piece(artist=self.artist_4, pieceid=1, min_bid=5, buy_now=50,
                  status=Piece.StatusInShow, location='C1'),
        ]
        Piece.objects.bulk_create(pieces)

        piece_1_2 = Piece(artist=self.artist_1, pieceid=2, min_bid=5, buy_now=50,
                          status=Piece.StatusInShow, location='A1')
        piece_1_2.save()

        piece_2_2 = Piece(artist=self.artist_2, pieceid=2, min_bid=5, buy_now=50,
                          status=Piece.StatusInShow, location='X1')
        piece_2_2.save()

        person = Person()
        person.save()

        bidder = Bidder(person=person)
        bidder.save()

        bidderid = BidderId(id='0365327', bidder=bidder)
        bidderid.save()

        Bid.objects.bulk_create([
            Bid(bidder=bidder, bidderid=bidderid, piece=piece_1_2, amount=10),
            Bid(bidder=bidder, bidderid=bidderid, piece=piece_2_2, amount=15),
            Bid(bidder=bidder, bidderid=bidderid, piece=piece_2_2, amount=20),
        ])

    def test_apply_space_fees(self):
        Artist.apply_space_fees(Artist.objects.all())

        self.assertEqual(Payment.objects.count(), 3)

        payment = Payment.objects.get(
            artist=self.artist_1,
            payment_type_id=settings.ARTSHOW_SPACE_FEE_PK)
        self.assertEqual(payment.amount, Decimal(-67.50))  # 2 * $15 + 1.5 * $25
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'GP:2, GT:1.5')

        payment = Payment.objects.get(
            artist=self.artist_2,
            payment_type_id=settings.ARTSHOW_SPACE_FEE_PK)
        self.assertEqual(payment.amount, Decimal(-70))  # 3 * $15 + 1 * $25
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'AP:3, AT:1')

        payment = Payment.objects.get(
            artist=self.artist_4,
            payment_type_id=settings.ARTSHOW_SPACE_FEE_PK)
        self.assertEqual(payment.amount, Decimal(-15))  # 1 * $15
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'GP:1')

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
        # Don't apply space fees so that the payment is positive.
        Artist.apply_winnings_and_commission(Artist.objects.all())
        Artist.create_cheques(Artist.objects.all())

        self.assertEqual(Payment.objects.filter(
            payment_type_id=settings.ARTSHOW_PAYMENT_SENT_PK).count(), 2)

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

        self.assertEqual(Payment.objects.count(), 7)

        payment = Payment.objects.get(
            artist=self.artist_1,
            payment_type_id=settings.ARTSHOW_SPACE_FEE_PK)
        self.assertEqual(payment.amount, Decimal(-67.50))  # 2 * $15 + 1.5 * $25
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'GP:2, GT:1.5')

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
        self.assertEqual(payment.amount, Decimal(-70))  # 3 * $15 + 1 * $25
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'AP:3, AT:1')

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

        payment = Payment.objects.get(
            artist=self.artist_4,
            payment_type_id=settings.ARTSHOW_SPACE_FEE_PK)
        self.assertEqual(payment.amount, Decimal(-15))  # 1 * $15
        self.assertEqual(payment.payment_type.name, 'Space Fee')
        self.assertEqual(payment.description, 'GP:1')
