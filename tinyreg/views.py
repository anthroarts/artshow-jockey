from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse

from oauthlib.oauth2 import AccessDeniedError, MismatchingStateError

from requests_oauthlib import OAuth2Session

from peeps.models import Person


def get_absolute_url(url):
    return settings.SITE_ROOT_URL + url


def get_oauth_session(request):
    return OAuth2Session(
        settings.OAUTH_CLIENT_ID,
        redirect_uri=get_absolute_url(reverse('oauth-complete')),
        scope=['pii:basic', 'pii:email', 'pii:phone', 'pii:address'],
        state=request.session.get('oauth_state'))


def oauth_redirect(request):
    oauth = get_oauth_session(request)
    authorization_url, state = \
        oauth.authorization_url(settings.OAUTH_AUTHORIZE_URL)

    request.session['oauth_state'] = state
    request.session['oauth_next'] = request.GET.get('next', '/')
    return redirect(authorization_url)


def oauth_complete(request):
    state = request.session.pop('oauth_state', None)
    next = request.session.pop('oauth_next', '/')

    if state is None:
        if request.user.is_authenticated:
            return HttpResponseRedirect(next)

        messages.error(request, 'Something went wrong. Please try again.')
        return HttpResponseRedirect(f'{settings.LOGIN_URL}?next={next}')

    oauth = get_oauth_session(request)

    try:
        oauth.fetch_token(
            settings.OAUTH_TOKEN_URL,
            client_secret=settings.OAUTH_CLIENT_SECRET,
            authorization_response=get_absolute_url(request.get_full_path()),
            include_client_id=True)
    except AccessDeniedError:
        messages.error(request, 'Access denied. Please try again.')
        return HttpResponseRedirect(f'{settings.LOGIN_URL}?next={next}')
    except MismatchingStateError:
        messages.error(request, 'Something went wrong. Please try again.')
        return HttpResponseRedirect(f'{settings.LOGIN_URL}?next={next}')

    user_info = oauth.get(settings.CONCAT_API + '/users/current').json()
    reg_id = str(user_info['id'])

    try:
        user = User.objects.get(username=reg_id)
    except User.DoesNotExist:
        user = User(username=reg_id)
        user.save()

    try:
        try:
            person = user.person
        except Person.DoesNotExist:
            person = Person.objects.filter(reg_id=reg_id)[:1].get()
            person.user = user
            person.save()
    except Person.DoesNotExist:
        person = Person(
            name=user_info['firstName'] + ' ' + user_info['lastName'],
            address1=user_info['addressLine1'],
            address2=user_info.get('addressLine2', ''),
            city=user_info['addressCity'],
            state=user_info['addressState'],
            postcode=user_info['addressZipcode'],
            country=user_info['addressCountry'],
            phone=user_info.get('phone', ''),
            email=user_info['email'],
            reg_id=reg_id,
            preferred_name=user_info.get('preferredName', ''),
            user=user)
        person.save()

    auth.login(request, user)
    return HttpResponseRedirect(next)
