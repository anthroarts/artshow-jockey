from django.contrib.auth.models import Permission, User
from django.core.urlresolvers import reverse
from django.test import Client, TestCase


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
            'bidder_registration_wizard-current_step': 0,
        })
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('artshow-bidderreg-wizard'), {
            'bidder_registration_wizard-current_step': 1,
            '1-name': 'Test Bidder',
            '1-reg_id': '123-456',
            '1-cell_contact': '(800) 555-0001',
            '1-other_contact': 'Marriott 626',
            '1-details_changed': False,
        })
        self.assertRedirects(response, reverse('artshow-bidderreg-final'))

    def test_registration_details_changed(self):
        self.client = Client()
        self.client.login(username='test', password='test')

        response = self.client.post(reverse('artshow-bidderreg-wizard'), {
            'bidder_registration_wizard-current_step': 0,
        })
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('artshow-bidderreg-wizard'), {
            'bidder_registration_wizard-current_step': 1,
            '1-name': 'Test Bidder',
            '1-reg_id': '123-456',
            '1-cell_contact': '(800) 555-0001',
            '1-other_contact': 'Marriott 626',
            '1-details_changed': True,
        })
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('artshow-bidderreg-wizard'), {
            'bidder_registration_wizard-current_step': 2,
            '2-address1': '100 Underhill Ln',
            '2-address2': 'Burrow 2',
            '2-city': 'Foxburrow',
            '2-state': 'CA',
            '2-postcode': '12345',
            '2-country': 'USA',
            '2-phone': '(800) 555-5555',
            '2-email': 'bidder@example.com',
        })
        self.assertRedirects(response, reverse('artshow-bidderreg-final'))
