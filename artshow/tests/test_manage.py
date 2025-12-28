from django.contrib.auth.models import User, Permission
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Artist
from peeps.models import Person


class ManageTests(TestCase):

    def setUp(self):
        user = User.objects.create_user(
            username='test', email='test@example.com', password='test')
        permission = Permission.objects.get(codename='is_artshow_staff')
        user.user_permissions.add(permission)
        user.save()

        person = Person(user=user)
        person.save()

        self.artist = Artist(person=person)
        self.artist.save()

        self.client = Client()
        self.client.login(username='test', password='test')

    def testManage(self):
        response = self.client.get(reverse('artshow-manage'))
        self.assertEqual(response.status_code, 200)

    def testManageArtist(self):
        response = self.client.get(reverse('artshow-manage-artist',
                                           args=(self.artist.artistid,)))
        self.assertEqual(response.status_code, 200)

    def testManageArtistDetails(self):
        response = self.client.get(reverse('artshow-manage-artist-details',
                                           args=(self.artist.artistid,)))
        self.assertEqual(response.status_code, 200)

    def testManagePersonDetails(self):
        response = self.client.get(reverse('artshow-manage-person-details',
                                           args=(self.artist.artistid,)))
        self.assertEqual(response.status_code, 200)

    def testManageSpaces(self):
        response = self.client.get(
            reverse('artshow-manage-spaces', args=(self.artist.artistid,)))
        self.assertEqual(response.status_code, 200)

    def testManagePieces(self):
        response = self.client.get(
            reverse('artshow-manage-pieces', args=(self.artist.artistid,)))
        self.assertEqual(response.status_code, 200)

    def testManageBidSheets(self):
        response = self.client.get(
            reverse('artshow-manage-bidsheets', args=(self.artist.artistid,)))
        self.assertEqual(response.status_code, 200)

    def testManageControlForms(self):
        response = self.client.get(reverse('artshow-manage-controlforms',
                                           args=(self.artist.artistid,)))
        self.assertEqual(response.status_code, 200)

    def testManageMakePayment(self):
        response = self.client.get(reverse('artshow-manage-make-payment',
                                           args=(self.artist.artistid,)))
        self.assertEqual(response.status_code, 200)
