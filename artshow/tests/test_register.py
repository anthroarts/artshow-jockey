import re

from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import Client, TestCase

class RegisterTests(TestCase):

    def test_load(self):
        c = Client()
        response = c.get(reverse('artshow-register'))
        self.assertEqual(response.status_code, 200)

    def test_register(self):
        c = Client()
        email_address = 'fox@example.com'
        response = c.post(reverse('artshow-register'), {
            'name': 'Mr. Fox',
            'address1': '100 Underhill Ln',
            'address2': 'Burrow 2',
            'city': 'Foxburrow',
            'state': 'CA',
            'postcode': '12345',
            'phone': '(800) 555-5555',
            'email': email_address,
            'email_confirm': email_address,
            'artist_name': 'The Fantastic Mr. Fox',
            'electronic_signature': 'Wiley Fox',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Wonderful!')
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [email_address])

        match = re.search(
            r'reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',
            message.body)
        self.assertIsNotNone(match)

        response = c.get(reverse('password_reset_confirm',
                                 kwargs=match.groupdict()))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['validlink'])
        self.assertTemplateUsed('accounts/password_reset_confirm.html')
