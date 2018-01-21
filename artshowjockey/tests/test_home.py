from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

class HomeTests(TestCase):

    def test_unauthenticated(self):
        c = Client()
        response = c.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in")
        self.assertContains(response, "Register")

    def test_superuser(self):
        password = 'test_password'
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@artshow',
            password=password)
        c = Client()
        c.login(username=admin.username, password=password)
        response = c.get(reverse('home'))
        self.assertRedirects(response, reverse('artshow-home'))

    def test_artist(self):
        password = 'test_password'
        artist = User.objects.create_user(
            username='artist',
            email='artist@artshow',
            password=password)
        c = Client()
        c.login(username=artist.username, password=password)
        response = c.get(reverse('home'))
        self.assertRedirects(response, reverse('artshow-manage'))

