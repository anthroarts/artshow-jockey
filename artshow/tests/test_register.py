# import re

# from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse


class RegisterTests(TestCase):

    def test_load(self):
        c = Client()
        response = c.get(reverse('artshow-register'))
        self.assertEqual(response.status_code, 200)

    # def test_register(self):
    #     c = Client()
    #     email_address = 'fox@example.com'
    #     response = c.post(reverse('artshow-register'), {
    #         'name': 'Mr. Fox',
    #         'address1': '100 Underhill Ln',
    #         'address2': 'Burrow 2',
    #         'city': 'Foxburrow',
    #         'state': 'CA',
    #         'postcode': '12345',
    #         'phone': '(800) 555-5555',
    #         'email': email_address,
    #         'email_confirm': email_address,
    #         'artist_name': 'The Fantastic Mr. Fox',
    #         'electronic_signature': 'Wiley Fox',
    #     })
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, 'Wonderful!')
    #     self.assertEqual(len(mail.outbox), 1)
    #     message = mail.outbox[0]
    #     self.assertEqual(message.to, [email_address])

    #     match = re.search(
    #         r'accounts/reset/(?P<uidb64>\w+)/(?P<token>\w+-\w+)/',
    #         message.body)
    #     self.assertIsNotNone(match)

    #     response = c.get(reverse('password_reset_confirm',
    #                              kwargs=match.groupdict()), follow=True)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertTrue(response.context['validlink'])
    #     self.assertTemplateUsed('accounts/password_reset_confirm.html')
