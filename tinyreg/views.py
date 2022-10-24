from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse

from requests_oauthlib import OAuth2Session

from peeps.models import Person


def get_absolute_url(url):
    return settings.SITE_ROOT_URL + url


def oauth_redirect(request):
    oauth = OAuth2Session(
        settings.OAUTH_CLIENT_ID,
        redirect_uri=get_absolute_url(reverse('oauth-complete')),
        scope=['pii:basic', 'pii:email', 'pii:phone', 'pii:address'])
    authorization_url, state = \
        oauth.authorization_url(settings.OAUTH_AUTHORIZE_URL)

    request.session['oauth_state'] = state
    request.session['oauth_next'] = request.GET.get('next', '/')
    return redirect(authorization_url)


def oauth_complete(request):
    oauth = OAuth2Session(
        settings.OAUTH_CLIENT_ID,
        redirect_uri=get_absolute_url(reverse('oauth-complete')),
        scope=['pii:basic', 'pii:email', 'pii:phone', 'pii:address'],
        state=request.session['oauth_state'])
    oauth.fetch_token(
        settings.OAUTH_TOKEN_URL,
        client_secret=settings.OAUTH_CLIENT_SECRET,
        authorization_response=get_absolute_url(request.get_full_path()),
        include_client_id=True)

    user_info = oauth.get(settings.CONCAT_API + '/users/current').json()

    try:
        person = Person.objects.get(reg_id=str(user_info['id']))
    except Person.DoesNotExist:
        person = Person(
            name=user_info['firstName'] + ' ' + user_info['lastName'],
            address1=user_info['addressLine1'],
            address2=user_info.get('addressLine2', ''),
            city=user_info['addressCity'],
            state=user_info['addressState'],
            postcode=user_info['addressZipcode'],
            country=user_info['addressCountry'],
            phone=user_info['phone'],
            email=user_info['email'],
            reg_id=user_info['id'],
            preferred_name=user_info.get('preferredName', ''))

    try:
        user = User.objects.get(username=person.reg_id)
    except User.DoesNotExist:
        user = User(username=person.reg_id)
        user.save()

    person.user = user
    person.save()

    auth.login(request, user)
    return HttpResponseRedirect(request.session.get('oauth_next', '/'))
