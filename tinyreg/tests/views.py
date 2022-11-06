import functools
from urllib.parse import parse_qs

from django.conf import settings
from django.http import (
    HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
)

from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from oauthlib.oauth2 import (
    FatalClientError, RequestValidator, WebApplicationServer
)

from . import models


class TestClient(object):
    def __init__(self, client_id):
        self.client_id = client_id


class TestRequestValidator(RequestValidator):
    valid_scopes = set(['pii:basic', 'pii:email', 'pii:phone', 'pii:address'])

    def __init__(self):
        self.valid_authorization_codes = set([])
        self.valid_bearer_tokens = set([])

    def authenticate_client(self, request):
        params = parse_qs(request.body)
        if params['client_id'][0] == settings.OAUTH_CLIENT_ID and \
           params['client_secret'][0] == settings.OAUTH_CLIENT_SECRET:
            request.client = TestClient(settings.OAUTH_CLIENT_ID)
            return True

        return False

    def confirm_redirect_uri(self, client_id, code, redirect_uri, client, request):
        return redirect_uri.startswith(settings.SITE_ROOT_URL)

    def invalidate_authorization_code(self, client_id, code, request):
        models.AuthorizationCode.objects.filter(code=code).delete()

    def save_authorization_code(self, client_id, code, request):
        authorization_code = models.AuthorizationCode(code=code['code'])
        authorization_code.save()

    def save_bearer_token(self, token, request):
        bearer_token = models.BearerToken(token=token['access_token'])
        bearer_token.save()

    def validate_bearer_token(self, token, scopes, request):
        return models.BearerToken.objects.filter(token=token).exists()

    def validate_client_id(self, client_id, request):
        return client_id == settings.OAUTH_CLIENT_ID

    def validate_code(self, client_id, code, client, request):
        return models.AuthorizationCode.objects.filter(code=code).exists()

    def validate_grant_type(self, client_id, grant_type, client, request):
        return grant_type == 'authorization_code'

    def validate_redirect_uri(self, client_id, redirect_uri, request):
        return redirect_uri.startswith(settings.SITE_ROOT_URL)

    def validate_response_type(self, client_id, response_type, client, request):
        return response_type == 'code'

    def validate_scopes(self, client_id, scopes, client, request):
        return set(scopes) <= self.valid_scopes


server = WebApplicationServer(TestRequestValidator())


def extract_params(request):
    uri = settings.SITE_ROOT_URL + request.get_full_path()
    http_method = request.method
    body = request.body
    headers = request.headers

    return (uri, http_method, body, headers)


def response_from_return(headers, body, status):
    response = HttpResponse(content=body, status=status)
    for k, v in headers.items():
        response[k] = v
    return response


def response_from_error(e):
    return HttpResponseBadRequest(
        'Evil client is unable to send a proper request. '
        + f'Error is: ${e.description}')


class AuthorizeView(View):
    def get(self, request):
        uri, http_method, body, headers = extract_params(request)

        try:
            scopes, credentials = server.validate_authorization_request(
                uri, http_method, body, headers)

            # Fake submitting the form immediately.
            headers, body, status = server.create_authorization_response(
                uri, 'POST', body, headers, scopes, credentials)

            return response_from_return(headers, body, status)
        except FatalClientError as e:
            return response_from_error(e)

    def post(self, request):
        pass


def protected_resource_view(scopes=None):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(request):
            try:
                scopes_list = scopes(request)
            except TypeError:
                scopes_list = scopes

            uri, http_method, body, headers = extract_params(request)

            valid, r = server.verify_request(
                uri, http_method, body, headers, scopes_list)

            if valid:
                return f(request)
            else:
                return HttpResponseForbidden()
        return wrapper
    return decorator


@method_decorator(csrf_exempt, name='dispatch')
class TokenView(View):
    def post(self, request):
        uri, http_method, body, headers = extract_params(request)

        headers, body, status = server.create_token_response(
            uri, http_method, body, headers, {})

        return response_from_return(headers, body, status)


@method_decorator(
    protected_resource_view(
        scopes=['pii:basic', 'pii:email', 'pii:phone', 'pii:address']),
    name='dispatch')
class CurrentUserView(View):
    current_user = {
        'id': 42,
        'firstName': 'Foxy',
        'lastName': 'McFoxerson',
        'addressLine1': '123 Main St.',
        'addressLine2': 'Apt 3',
        'addressCity': 'New York',
        'addressState': 'NY',
        'addressZipcode': '12345',
        'addressCountry': 'US',
        'phone': '800-555-1234',
        'email': 'fox@example.com',
    }

    def get(self, request):
        return JsonResponse(self.current_user)
