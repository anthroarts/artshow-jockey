from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Artist, Bid, Bidder, BidderId, Piece
from peeps.models import Person


class BidTests(TestCase):

    def setUp(self):
        artist_person = Person()
        artist_person.save()

        artist = Artist(person=artist_person, publicname='Artist', artistid=1)
        artist.save()

        self.piece1 = Piece(
            artist=artist, pieceid=1, min_bid=5, buy_now=50,
            status=Piece.StatusInShow, location='A1')
        self.piece1.save()

        bidder_user = User.objects.create_user(
            username='bidder', email='bidder@example.com', password='test')
        bidder_user.save()

        self.bidder_person = Person(user=bidder_user, reg_id='42')
        self.bidder_person.save()

        person2 = Person(reg_id='69')
        person2.save()

        self.bidder2 = Bidder(person=person2)
        self.bidder2.save()

        self.bidderid2 = BidderId(id='0019', bidder=self.bidder2)
        self.bidderid2.save()

        self.client = Client()

    def logIn(self):
        self.client.login(username='bidder', password='test')

    def register(self):
        self.bidder = Bidder(person=self.bidder_person)
        self.bidder.save()

        self.bidderid = BidderId(id='0365327', bidder=self.bidder)
        self.bidderid.save()

    def testBidLoggedOut(self):
        index_url = reverse('artshow-bid')
        response = self.client.get(index_url)
        self.assertRedirects(
            response, reverse('artshow-bid-login') + '?next=' + index_url)

    def testBidUnregistered(self):
        self.logIn()
        response = self.client.get(reverse('artshow-bid'))
        self.assertRedirects(response, reverse('artshow-bid-register'))

    def testBid(self):
        self.logIn()
        self.register()
        response = self.client.get(reverse('artshow-bid'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['bidder'], self.bidder)
        self.assertFalse(response.context['show_has_bids'])

    def testNoBids(self):
        self.logIn()
        self.register()
        Bid.objects.bulk_create([
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=10),
        ])
        self.piece1.apply_won_status()

        response = self.client.get(reverse('artshow-bid'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['bidder'], self.bidder)
        self.assertTrue(response.context['show_has_bids'])
        self.assertListEqual(response.context['pieces_won'], [])
        self.assertListEqual(response.context['pieces_not_won'], [])
        self.assertListEqual(response.context['pieces_in_voice_auction'], [])

    def testNoWinningBids(self):
        self.logIn()
        self.register()
        Bid.objects.bulk_create([
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=10),
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=20),
        ])
        self.piece1.apply_won_status()

        response = self.client.get(reverse('artshow-bid'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['bidder'], self.bidder)
        self.assertTrue(response.context['show_has_bids'])
        self.assertListEqual(response.context['pieces_won'], [])
        self.assertListEqual(response.context['pieces_in_voice_auction'], [])

        pieces_not_won = response.context['pieces_not_won']
        self.assertListEqual(pieces_not_won, [self.piece1])
        self.assertEqual(pieces_not_won[0].top_bid, 20)
        self.assertEqual(pieces_not_won[0].top_bidder, self.bidder2.pk)

    def testWinningBid(self):
        self.logIn()
        self.register()
        Bid.objects.bulk_create([
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=10),
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=20),
        ])
        self.piece1.apply_won_status()

        response = self.client.get(reverse('artshow-bid'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['bidder'], self.bidder)
        self.assertTrue(response.context['show_has_bids'])
        self.assertListEqual(response.context['pieces_not_won'], [])
        self.assertListEqual(response.context['pieces_in_voice_auction'], [])

        pieces_won = response.context['pieces_won']
        self.assertListEqual(pieces_won, [self.piece1])
        self.assertEqual(pieces_won[0].top_bid, 20)
        self.assertEqual(pieces_won[0].top_bidder, self.bidder.pk)

    def testWaitingVoiceAuction(self):
        self.logIn()
        self.register()
        Bid.objects.bulk_create([
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=10),
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=20),
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=30),
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=40),
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=50),
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=60),
        ])
        self.piece1.apply_won_status()

        response = self.client.get(reverse('artshow-bid'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['bidder'], self.bidder)
        self.assertTrue(response.context['show_has_bids'])
        self.assertListEqual(response.context['pieces_won'], [])
        self.assertListEqual(response.context['pieces_not_won'], [])

        pieces_in_voice_auction = response.context['pieces_in_voice_auction']
        self.assertListEqual(pieces_in_voice_auction, [self.piece1])
        self.assertEqual(pieces_in_voice_auction[0].top_bid, 60)
        self.assertEqual(pieces_in_voice_auction[0].top_bidder, self.bidder.pk)

    def testWonInVoiceAuction(self):
        self.logIn()
        self.register()
        Bid.objects.bulk_create([
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=10),
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=20),
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=30),
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=40),
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=50),
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=60),
        ])
        self.piece1.apply_won_status()
        Bid.objects.bulk_create([
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=70),
        ])
        self.piece1.status = Piece.StatusWon
        self.piece1.save()

        response = self.client.get(reverse('artshow-bid'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['bidder'], self.bidder)
        self.assertTrue(response.context['show_has_bids'])
        self.assertListEqual(response.context['pieces_not_won'], [])
        self.assertListEqual(response.context['pieces_in_voice_auction'], [])

        pieces_won = response.context['pieces_won']
        self.assertListEqual(pieces_won, [self.piece1])
        self.assertEqual(pieces_won[0].top_bid, 70)
        self.assertEqual(pieces_won[0].top_bidder, self.bidder.pk)

    def testLostInVoiceAuction(self):
        self.logIn()
        self.register()
        Bid.objects.bulk_create([
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=10),
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=20),
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=30),
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=40),
            Bid(bidder=self.bidder, bidderid=self.bidderid, piece=self.piece1, amount=50),
            Bid(bidder=self.bidder2, bidderid=self.bidderid2, piece=self.piece1, amount=60),
        ])
        self.piece1.apply_won_status()
        Bid.objects.bulk_create([
            Bid(bidder=self.bidder2, bidderid=self.bidderid, piece=self.piece1, amount=100),
        ])
        self.piece1.status = Piece.StatusWon
        self.piece1.save()

        response = self.client.get(reverse('artshow-bid'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['bidder'], self.bidder)
        self.assertTrue(response.context['show_has_bids'])
        self.assertListEqual(response.context['pieces_won'], [])
        self.assertListEqual(response.context['pieces_in_voice_auction'], [])

        pieces_not_won = response.context['pieces_not_won']
        self.assertListEqual(pieces_not_won, [self.piece1])
        self.assertEqual(pieces_not_won[0].top_bid, 100)
        self.assertEqual(pieces_not_won[0].top_bidder, self.bidder2.pk)

    def testBidLoggedInAlready(self):
        self.logIn()
        response = self.client.get(reverse('artshow-bid-login'), follow=True)
        self.assertRedirects(response, reverse('artshow-bid-register'))

    def testBidLogin(self):
        response = self.client.get(reverse('artshow-bid-login'))
        self.assertEqual(response.status_code, 200)

    def testBidRegisterLoggedOut(self):
        register_url = reverse('artshow-bid-register')
        response = self.client.get(register_url)
        self.assertRedirects(
            response, reverse('artshow-bid-login') + '?next=' + register_url)

    def testBidRegisterAlready(self):
        self.logIn()
        self.register()
        response = self.client.get(reverse('artshow-bid-register'))
        self.assertRedirects(response, reverse('artshow-bid'))

    def testBidRegister(self):
        self.logIn()
        response = self.client.get(reverse('artshow-bid-register'))
        self.assertEqual(response.status_code, 200)
