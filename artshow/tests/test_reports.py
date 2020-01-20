from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse


class ReportTests(TestCase):

    def setUp(self):
        user = User.objects.create_user(
            username='test', email='test@example.com', password='test')
        permission = Permission.objects.get(codename='is_artshow_staff')
        user.user_permissions.add(permission)
        user.save()

    def test_show_summary(self):
        c = Client()
        c.login(username='test', password='test')
        response = c.get(reverse('artshow-summary'))
        self.assertEqual(response.status_code, 200)
