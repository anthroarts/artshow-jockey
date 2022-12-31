import requests

from django.conf import settings
from django.contrib.auth.models import User
from django.test import LiveServerTestCase
from django.urls import reverse

from peeps.models import Person

from .views import CurrentUserView

# Uncomment for detailed oauthlib logs
# import logging
# import sys
# log = logging.getLogger('oauthlib')
# log.addHandler(logging.StreamHandler(sys.stdout))
# log.setLevel(logging.DEBUG)


class OAuthTests(LiveServerTestCase):
    def setUp(self):
        settings.SITE_ROOT_URL = self.live_server_url
        settings.OAUTH_AUTHORIZE_URL = self.live_server_url + '/test/oauth/authorize'
        settings.OAUTH_TOKEN_URL = self.live_server_url + '/test/oauth/token'
        settings.CONCAT_API = self.live_server_url + '/test/oauth/api'

    def test_create_user(self):
        CurrentUserView.current_user = {
            'id': 42,
            'firstName': 'Foxy',
            'lastName': 'McFoxerson',
            'preferredName': 'Mr. Fox',
            'addressLine1': '123 Main St.',
            'addressLine2': 'Apt 3',
            'addressCity': 'New York',
            'addressState': 'NY',
            'addressZipcode': '12345',
            'addressCountry': 'US',
            'phone': '800-555-1234',
            'email': 'fox@example.com',
        }

        url = reverse('oauth-redirect')
        response = requests.get(self.live_server_url + url)
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username="42")
        person = user.person
        self.assertEquals(person.reg_id, "42")
        self.assertEquals(person.name, 'Foxy McFoxerson')
        self.assertEquals(person.preferred_name, 'Mr. Fox')
        self.assertEquals(person.address1, '123 Main St.')
        self.assertEquals(person.address2, 'Apt 3')
        self.assertEquals(person.city, 'New York')
        self.assertEquals(person.state, 'NY')
        self.assertEquals(person.postcode, '12345')
        self.assertEquals(person.country, 'US')
        self.assertEquals(person.phone, '800-555-1234')
        self.assertEquals(person.email, 'fox@example.com')

    def test_create_user_optional_fields(self):
        CurrentUserView.current_user = {
            'id': 42,
            'firstName': 'Foxy',
            'lastName': 'McFoxerson',
            'addressLine1': '123 Main St.',
            'addressCity': 'New York',
            'addressState': 'NY',
            'addressZipcode': '12345',
            'addressCountry': 'US',
            'email': 'fox@example.com',
        }

        url = reverse('oauth-redirect')
        response = requests.get(self.live_server_url + url)
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username="42")
        person = user.person
        self.assertEquals(person.reg_id, "42")
        self.assertEquals(person.name, 'Foxy McFoxerson')
        self.assertEquals(person.preferred_name, '')
        self.assertEquals(person.address1, '123 Main St.')
        self.assertEquals(person.address2, '')
        self.assertEquals(person.city, 'New York')
        self.assertEquals(person.state, 'NY')
        self.assertEquals(person.postcode, '12345')
        self.assertEquals(person.country, 'US')
        self.assertEquals(person.phone, '')
        self.assertEquals(person.email, 'fox@example.com')

    def test_log_in_with_existing_person(self):
        CurrentUserView.current_user = {
            'id': 42,
            'firstName': 'Ignored',
            'lastName': 'Ignored',
            'preferredName': 'Ignored',
            'addressLine1': 'Ignored',
            'addressLine2': 'Ignored',
            'addressCity': 'Ignored',
            'addressState': 'Ignored',
            'addressZipcode': 'Ignored',
            'addressCountry': 'Ignored',
            'phone': 'Ignored',
            'email': 'Ignored',
        }

        person = Person(
            name='Foxy McFoxerson',
            address1='123 Main St.',
            address2='Apt 3',
            city='New York',
            state='NY',
            postcode='12345',
            country='US',
            phone='800-555-1234',
            email='fox@example.com',
            reg_id='42',
            preferred_name='Mr. Fox')
        person.save()

        url = reverse('oauth-redirect')
        response = requests.get(self.live_server_url + url)
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username="42")
        self.assertEquals(user.person.pk, person.pk)
        self.assertEquals(user.person.reg_id, "42")
        self.assertEquals(user.person.name, 'Foxy McFoxerson')
        self.assertEquals(user.person.preferred_name, 'Mr. Fox')
        self.assertEquals(user.person.address1, '123 Main St.')
        self.assertEquals(user.person.address2, 'Apt 3')
        self.assertEquals(user.person.city, 'New York')
        self.assertEquals(user.person.state, 'NY')
        self.assertEquals(user.person.postcode, '12345')
        self.assertEquals(user.person.country, 'US')
        self.assertEquals(user.person.phone, '800-555-1234')
        self.assertEquals(user.person.email, 'fox@example.com')

    def test_log_in_with_existing_user_and_duplicate_person(self):
        CurrentUserView.current_user = {
            'id': 42,
            'firstName': 'Ignored',
            'lastName': 'Ignored',
            'preferredName': 'Ignored',
            'addressLine1': 'Ignored',
            'addressLine2': 'Ignored',
            'addressCity': 'Ignored',
            'addressState': 'Ignored',
            'addressZipcode': 'Ignored',
            'addressCountry': 'Ignored',
            'phone': 'Ignored',
            'email': 'Ignored',
        }

        user = User(username='42')
        user.save()

        person = Person(
            name='Foxy McFoxerson',
            address1='123 Main St.',
            address2='Apt 3',
            city='New York',
            state='NY',
            postcode='12345',
            country='US',
            phone='800-555-1234',
            email='fox@example.com',
            reg_id='42',
            preferred_name='Mr. Fox',
            user=user)
        person.save()

        duplicate_person = Person(
            name='Foxy McFoxerson',
            address1='123 Main Street',
            address2='Apartment 3',
            city='New York',
            state='NY',
            postcode='12345',
            country='USA',
            phone='800-555-1234',
            email='fox@example.com',
            reg_id='42',
            preferred_name='')
        duplicate_person.save()

        url = reverse('oauth-redirect')
        response = requests.get(self.live_server_url + url)
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username="42")
        self.assertEquals(user.person.pk, person.pk)
        self.assertEquals(user.person.reg_id, "42")
        self.assertEquals(user.person.name, 'Foxy McFoxerson')
        self.assertEquals(user.person.preferred_name, 'Mr. Fox')
        self.assertEquals(user.person.address1, '123 Main St.')
        self.assertEquals(user.person.address2, 'Apt 3')
        self.assertEquals(user.person.city, 'New York')
        self.assertEquals(user.person.state, 'NY')
        self.assertEquals(user.person.postcode, '12345')
        self.assertEquals(user.person.country, 'US')
        self.assertEquals(user.person.phone, '800-555-1234')
        self.assertEquals(user.person.email, 'fox@example.com')

    def test_log_in_with_existing_user_without_person(self):
        CurrentUserView.current_user = {
            'id': 42,
            'firstName': 'Foxy',
            'lastName': 'McFoxerson',
            'preferredName': 'Mr. Fox',
            'addressLine1': '123 Main St.',
            'addressLine2': 'Apt 3',
            'addressCity': 'New York',
            'addressState': 'NY',
            'addressZipcode': '12345',
            'addressCountry': 'US',
            'phone': '800-555-1234',
            'email': 'fox@example.com',
        }

        user = User(username='42')
        user.save()

        url = reverse('oauth-redirect')
        response = requests.get(self.live_server_url + url)
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username="42")
        person = user.person
        self.assertEquals(person.reg_id, "42")
        self.assertEquals(person.name, 'Foxy McFoxerson')
        self.assertEquals(person.preferred_name, 'Mr. Fox')
        self.assertEquals(person.address1, '123 Main St.')
        self.assertEquals(person.address2, 'Apt 3')
        self.assertEquals(person.city, 'New York')
        self.assertEquals(person.state, 'NY')
        self.assertEquals(person.postcode, '12345')
        self.assertEquals(person.country, 'US')
        self.assertEquals(person.phone, '800-555-1234')
        self.assertEquals(person.email, 'fox@example.com')
