from django.contrib.auth.models import User, Permission
from django.test import Client, TestCase
from django.urls import reverse

from .. import testdata


class ManageTests(TestCase):
    fixtures = ['artshowpaymenttypes', 'artshowspaces']

    def setUp(self):
        user = User.objects.create_user(
            username='test', email='test@example.com', password='test')
        permission = Permission.objects.get(codename='is_artshow_staff')
        user.user_permissions.add(permission)
        user.save()

        self.client = Client()
        self.client.login(username='test', password='test')

    def testCloseShow(self):
        testdata.create('test@example.com')

        response = self.client.post(reverse('artshow-workflow-close-show'))
        self.assertEqual(response.status_code, 200)
