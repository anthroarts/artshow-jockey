import requests

from django.test import LiveServerTestCase
from django.urls import reverse

# Uncomment for detailed oauthlib logs
# import logging
# import sys
# log = logging.getLogger('oauthlib')
# log.addHandler(logging.StreamHandler(sys.stdout))
# log.setLevel(logging.DEBUG)


class OAuthTests(LiveServerTestCase):

    def test_login(self):
        with self.settings(
                SITE_ROOT_URL=self.live_server_url,
                OAUTH_AUTHORIZE_URL=self.live_server_url + '/test/oauth/authorize',
                OAUTH_TOKEN_URL=self.live_server_url + '/test/oauth/token',
                CONCAT_API=self.live_server_url + '/test/oauth/api'):
            url = reverse('oauth-redirect')
            response = requests.get(self.live_server_url + url)
            self.assertEqual(response.status_code, 200)
