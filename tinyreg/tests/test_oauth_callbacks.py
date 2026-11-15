from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.http import JsonResponse
from django.test import Client, LiveServerTestCase
from django.urls import reverse
from django.utils import timezone

from peeps.models import Person

from .views import CurrentUserView, TokenView


class OAuthCallbackTests(LiveServerTestCase):
    def setUp(self):
        self.enterContext(self.settings(
            SITE_ROOT_URL=self.live_server_url,
            OAUTH_AUTHORIZE_URL=self.live_server_url + '/test/oauth/authorize',
            OAUTH_TOKEN_URL=self.live_server_url + '/test/oauth/token',
            CONCAT_API=self.live_server_url + '/test/oauth/api',
        ))
        self.enterContext(patch.object(CurrentUserView, 'current_user', {
            'id': 42,
            'firstName': 'Foxy',
            'lastName': 'McFoxerson',
            'addressLine1': '123 Main St.',
            'addressCity': 'New York',
            'addressState': 'NY',
            'addressZipcode': '12345',
            'addressCountry': 'US',
            'email': 'fox@example.com',
        }))
        # Spy on the local provider, leaving the OAuth client's validation real.
        self.token_request = self.enterContext(patch.object(
            TokenView, 'post', autospec=True, side_effect=TokenView.post))
        self.profile_request = self.enterContext(patch.object(
            CurrentUserView, 'get', autospec=True,
            side_effect=CurrentUserView.get))

    def start_login(self, client=None, next='/manage/'):
        client = client or self.client
        response = client.get(reverse('oauth-redirect'), {'next': next})
        self.assertEqual(response.status_code, 302)
        authorization = client.get(response.url)
        self.assertEqual(authorization.status_code, 302)
        return authorization['Location']

    def callback_with_state(self, callback, state):
        parts = urlsplit(callback)
        params = parse_qs(parts.query)
        if state is None:
            params.pop('state')
        else:
            params['state'] = [state]
        return parts._replace(query=urlencode(params, doseq=True)).geturl()

    def assert_login_error(self, callback, next='/manage/',
                           message='Something went wrong. Please try again.',
                           token_requests=0):
        users = list(User.objects.order_by('pk').values())
        people = list(Person.objects.order_by('pk').values())

        response = self.client.get(callback)

        self.assertRedirects(response, f'{settings.LOGIN_URL}?next={next}',
                             fetch_redirect_response=False)
        login_response = self.client.get(response.url)
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(
            [str(item) for item in get_messages(login_response.wsgi_request)],
            [message])
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotIn('oauth_state', self.client.session)
        self.assertNotIn('oauth_next', self.client.session)
        self.assertEqual(list(User.objects.order_by('pk').values()), users)
        self.assertEqual(list(Person.objects.order_by('pk').values()), people)
        self.assertEqual(self.token_request.call_count, token_requests)
        self.profile_request.assert_not_called()

    def assert_logged_in(self, callback, next='/manage/'):
        response = self.client.get(callback)
        self.assertRedirects(response, next, fetch_redirect_response=False)
        user = User.objects.get(username='42')
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))
        self.assertEqual(user.person.reg_id, '42')
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Person.objects.count(), 1)
        self.assertNotIn('oauth_state', self.client.session)
        self.assertNotIn('oauth_next', self.client.session)
        self.token_request.assert_called_once()
        self.profile_request.assert_called_once()

    def test_mismatched_state_cannot_create_records(self):
        callback = self.start_login()
        self.assert_login_error(self.callback_with_state(callback, 'wrong'))

    def test_missing_state_cannot_create_records(self):
        callback = self.start_login()
        self.assert_login_error(self.callback_with_state(callback, None))

    def test_empty_state_cannot_create_records(self):
        callback = self.start_login()
        self.assert_login_error(self.callback_with_state(callback, ''))

    def test_invalid_state_cannot_log_in_existing_user_or_link_person(self):
        User.objects.create(username='42')
        Person.objects.create(reg_id='42', name='Existing person')
        for state in ('wrong', None, ''):
            with self.subTest(state=state):
                callback = self.start_login()
                self.assert_login_error(
                    self.callback_with_state(callback, state))

    def test_callback_without_session(self):
        callback = self.start_login()
        self.client.cookies.clear()
        self.assert_login_error(callback, next='/')

    def test_callback_with_expired_session(self):
        callback = self.start_login()
        session = self.client.session
        session.set_expiry(timezone.now() - timedelta(seconds=1))
        session.save()
        self.assert_login_error(callback, next='/')

    def test_callback_without_saved_state(self):
        for state in (None, ''):
            with self.subTest(state=state):
                callback = self.start_login()
                session = self.client.session
                session['oauth_state'] = state
                session.save()
                self.assert_login_error(callback)

    def test_missing_access_token(self):
        callback = self.start_login()
        self.token_request.side_effect = None
        self.token_request.return_value = JsonResponse({'token_type': 'Bearer'})
        self.assert_login_error(callback, token_requests=1)

    def test_denied_authorization(self):
        self.start_login()
        params = urlencode({
            'error': 'access_denied',
            'state': self.client.session['oauth_state'],
        })
        self.assert_login_error(
            reverse('oauth-complete') + '?' + params,
            message='Access denied. Please try again.')

    def test_denied_authorization_still_requires_matching_state(self):
        self.start_login()
        self.assert_login_error(
            reverse('oauth-complete') + '?error=access_denied&state=wrong')

    def test_successful_callback_consumes_state_and_preserves_destination(self):
        self.assert_logged_in(self.start_login())

    def test_valid_callback_links_existing_user_and_person(self):
        user = User.objects.create(username='42')
        person = Person.objects.create(reg_id='42', name='Existing person')
        self.assert_logged_in(self.start_login())
        person.refresh_from_db()
        self.assertEqual(person.user_id, user.pk)
        self.assertEqual(person.name, 'Existing person')

    def test_callback_cannot_be_replayed_after_logout(self):
        callback = self.start_login()
        self.assert_logged_in(callback)
        self.client.logout()
        self.token_request.reset_mock()
        self.profile_request.reset_mock()
        self.assert_login_error(callback, next='/')

    def test_failed_callback_requires_fresh_login_state(self):
        callback = self.start_login()
        old_state = self.client.session['oauth_state']
        self.assert_login_error(self.callback_with_state(callback, 'wrong'))
        self.assert_login_error(callback, next='/')
        retry = self.start_login()
        self.assertNotEqual(self.client.session['oauth_state'], old_state)
        self.assert_logged_in(retry)

    def assert_concurrent_logins(self, reverse_order=False):
        first = self.start_login()
        state = self.client.session['oauth_state']
        second = self.start_login()
        self.assertEqual(self.client.session['oauth_state'], state)
        if reverse_order:
            first, second = second, first

        self.assert_logged_in(first)
        # Another tab's callback must not reauthenticate or change identity.
        CurrentUserView.current_user['id'] = 99
        self.assert_logged_in(second, next='/')

    def test_concurrent_logins_complete_in_start_order(self):
        self.assert_concurrent_logins()

    def test_concurrent_logins_complete_in_reverse_order(self):
        self.assert_concurrent_logins(reverse_order=True)

    def test_concurrent_logins_still_require_matching_state(self):
        first = self.start_login()
        self.start_login()
        self.assert_login_error(self.callback_with_state(first, 'wrong'))

    def test_state_from_another_browser_session_is_rejected(self):
        self.start_login()
        other_client = Client()
        callback = self.start_login(client=other_client)
        self.assertNotEqual(self.client.session['oauth_state'],
                            other_client.session['oauth_state'])
        self.assert_login_error(callback)

    def test_callback_does_not_replace_an_authenticated_user(self):
        callback = self.start_login()
        user = User.objects.create(username='already-logged-in')
        self.client.force_login(user)

        response = self.client.get(callback)

        self.assertRedirects(response, '/manage/',
                             fetch_redirect_response=False)
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(Person.objects.exists())
        self.token_request.assert_not_called()
        self.profile_request.assert_not_called()
