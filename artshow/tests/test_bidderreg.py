from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Bidder


class BidEntryTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='test', email='test@example.com', password='test')
        permission = Permission.objects.get(codename='is_artshow_kiosk')
        self.user.user_permissions.add(permission)
        self.user.save()

    def test_registration(self):
        self.client = Client()
        self.client.login(username='test', password='test')

        response = self.client.post(reverse('artshow-bidderreg-wizard'), {
            'name': 'Test Bidder',
            'reg_id': '123-456',
            'at_con_contact': 'Marriott 626',
            'address1': '100 Underhill Ln',
            'address2': 'Burrow 2',
            'city': 'Foxburrow',
            'state': 'CA',
            'postcode': '12345',
            'country': 'USA',
            'phone': '(800) 555-5555',
            'email': 'bidder@example.com',
        })
        self.assertRedirects(
            response, reverse('artshow-bidderreg-final'))

        bidder = Bidder.objects.get(person__reg_id='123-456')
        self.assertEqual(bidder.person.name, 'Test Bidder')
        self.assertEqual(bidder.at_con_contact, 'Marriott 626')
        self.assertEqual(bidder.person.address1, '100 Underhill Ln')
        self.assertEqual(bidder.person.address2, 'Burrow 2')
        self.assertEqual(bidder.person.city, 'Foxburrow')
        self.assertEqual(bidder.person.state, 'CA')
        self.assertEqual(bidder.person.postcode, '12345')
        self.assertEqual(bidder.person.country, 'USA')
        self.assertEqual(bidder.person.phone, '(800) 555-5555')
        self.assertEqual(bidder.person.email, 'bidder@example.com')
