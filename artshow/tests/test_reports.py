from decimal import Decimal
from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Artist, Allocation, Location, Space
from peeps.models import Person


class ReportTests(TestCase):
    fixtures = ['artshowpaymenttypes', 'artshowspaces']

    def setUp(self):
        user = User.objects.create_user(
            username='test', email='test@example.com', password='test')
        permission = Permission.objects.get(codename='is_artshow_staff')
        user.user_permissions.add(permission)
        user.save()

        person = Person()
        person.save()

        artist_1 = Artist(person=person, publicname='Artist 1', artistid=1)
        artist_2 = Artist(person=person, publicname='Artist 2', artistid=2)
        Artist.objects.bulk_create([
            artist_1, artist_2,
            Artist(person=person, publicname='Artist 3', artistid=3)
        ])

        gp = Space.objects.get(shortname='GP')
        gt = Space.objects.get(shortname='GT')
        ap = Space.objects.get(shortname='AP')
        at = Space.objects.get(shortname='AT')

        Allocation.objects.bulk_create([
            Allocation(artist=artist_1, space=gp, requested=1.5),
            Allocation(artist=artist_1, space=ap, requested=1),
            Allocation(artist=artist_1, space=at, requested=1),
            Allocation(artist=artist_2, space=gp, requested=1),
        ])

        Location.objects.bulk_create([
            Location(name='A1', type=gp, artist_1=artist_1),
            Location(name='A2', type=gp, artist_1=artist_1, artist_2=artist_2, space_is_split=True),
            Location(name='A3', type=gp, artist_1=artist_1, space_is_split=True),
            Location(name='A4', type=gp, artist_1=artist_2, half_space=True),
            Location(name='B1', type=gt, artist_1=artist_1),
            Location(name='X1', type=ap),
            Location(name='Y1', type=at, artist_1=artist_1),
        ])

    def test_show_summary(self):
        c = Client()
        c.login(username='test', password='test')
        response = c.get(reverse('artshow-summary'))
        self.assertEqual(response.status_code, 200)

    def test_allocations_waiting(self):
        c = Client()
        c.login(username='test', password='test')
        response = c.get(reverse('artshow-report-allocations-waiting'))
        self.assertEqual(response.context['sections'], [
            ('Short Allocations', {
                'Adult Panel': [
                    {
                        'artistid': 1,
                        'artist': 'Artist 1 (1)',
                        'requested': Decimal(1),
                        'allocated': Decimal(0),
                    }
                ],
            }),
            ('Over Allocations', {
                'General Panel': [
                    {
                        'artistid': 1,
                        'artist': 'Artist 1 (1)',
                        'requested': Decimal(1.5),
                        'allocated': Decimal(2),
                    }
                ],
                'General Table': [
                    {
                        'artistid': 1,
                        'artist': 'Artist 1 (1)',
                        'requested': Decimal(0),
                        'allocated': Decimal(1),
                    }
                ]
            })
        ])

    def test_artist_panel_report(self):
        c = Client()
        c.login(username='test', password='test')
        response = c.get(reverse('artshow-report-artist-to-panel'))
        self.assertEqual(response.context['artists'][0].locations,
                         ['A1', 'A2', 'A3', 'B1', 'Y1'])
        self.assertEqual(response.context['artists'][1].locations,
                         ['A2', 'A4'])
        self.assertEqual(response.context['artists'][2].locations,
                         [])
