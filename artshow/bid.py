from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from django import forms

from .models import Bid, Bidder
from .telegram import send_message as send_telegram_message
from .utils import artshow_settings

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from random import randint

LOGIN_URL = '/bid/login/'


class RegisterForm(forms.Form):
    name = forms.CharField(
        label="Legal name", label_suffix="",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.CharField(
        label="E-mail address", label_suffix="", max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(
        label="Phone number", label_suffix="", max_length=40, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    address1 = forms.CharField(
        label="Address", label_suffix="", max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    address2 = forms.CharField(
        label="Address 2", label_suffix="", max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    city = forms.CharField(
        label_suffix="", max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    state = forms.CharField(
        label_suffix="", max_length=40, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    postcode = forms.CharField(
        label="ZIP code", label_suffix="", max_length=20, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    country = forms.CharField(
        label_suffix="", max_length=40, required=False, empty_value='USA',
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    at_con_contact = forms.CharField(
        label="At-con contact (optional)", label_suffix="", max_length=100,
        required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))


class ConfirmationForm(forms.Form):
    code = forms.CharField(
        max_length=40, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Code',
        }))


@login_required(login_url=LOGIN_URL)
def index(request):
    try:
        bidder = Bidder.objects.get(person__user=request.user)
    except Bidder.DoesNotExist:
        return redirect('artshow-bid-register')

    pieces_won, pieces_not_won, pieces_in_voice_auction = bidder.get_results()
    show_has_bids = Bid.objects.filter(invalid=False).exists()

    email_confirmation_form = None
    if bidder.person.email_confirmation_code:
        email_confirmation_form = ConfirmationForm()

    response = render(request, "artshow/bid_index.html", {
        'bidder': bidder,
        'show_has_bids': show_has_bids,
        'pieces_won': pieces_won,
        'pieces_not_won': pieces_not_won,
        'pieces_in_voice_auction': pieces_in_voice_auction,
        'email_confirmation_form': email_confirmation_form,
    })
    # The Telegram login widget opens a popup window and needs access to the
    # opener property.
    response['Cross-Origin-Opener-Policy'] = 'unsafe-none'
    return response


def login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(request.GET.get('next', reverse('artshow-bid')))

    return render(request, "artshow/bid_login.html")


@login_required(login_url=LOGIN_URL)
def register(request):
    if Bidder.objects.filter(person__user=request.user).exists():
        return redirect('artshow-bid')

    person = request.user.person
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            person.name = form.cleaned_data['name']
            person.address1 = form.cleaned_data['address1']
            person.address2 = form.cleaned_data['address2']
            person.city = form.cleaned_data['city']
            person.state = form.cleaned_data['state']
            person.postcode = form.cleaned_data['postcode']
            person.country = form.cleaned_data['country']
            person.phone = form.cleaned_data['phone']
            person.email = form.cleaned_data['email']
            person.save()

            bidder = Bidder.objects.create(
                person=request.user.person,
                at_con_contact=form.cleaned_data['at_con_contact']
            )
            bidder.save()

            return redirect('artshow-bid')
    else:
        form = RegisterForm({
            'name': person.name,
            'email': person.email,
            'phone': person.phone,
            'address1': person.address1,
            'address2': person.address2,
            'city': person.city,
            'state': person.state,
            'postcode': person.postcode,
            'country': person.country,
        })

    return render(request, "artshow/bid_register.html", {'form': form})


@login_required(login_url=LOGIN_URL)
@require_POST
def send_email_code(request):
    person = request.user.person
    if person.email_confirmed:
        return redirect('artshow-bid')

    person.email_confirmation_code = str(randint(0, 999999)).zfill(6)
    person.save()

    text_content = render_to_string('artshow/bid_email_confirmation.txt', {
        'code': person.email_confirmation_code,
    })
    send_mail(
        subject='Confirm your e-mail address',
        message=text_content,
        from_email=artshow_settings.ARTSHOW_EMAIL_SENDER,
        recipient_list=[person.email],
    )

    return redirect('artshow-bid')


@login_required(login_url=LOGIN_URL)
@require_POST
def confirm_email(request):
    person = request.user.person
    if person.email_confirmed:
        return redirect('artshow-bid')

    error = 'Invalid form data.'
    form = ConfirmationForm(request.POST)
    if form.is_valid():
        error = 'Invalid confirmation code.'
        if form.cleaned_data['code'] == person.email_confirmation_code:
            person.email_confirmed = True
            person.email_confirmation_code = ''
            person.save()

            return redirect('artshow-bid')

    form = ConfirmationForm()
    return render(request, "artshow/bid_confirm_email.html", {
        'error': error,
        'form': form
    })


@login_required(login_url=LOGIN_URL)
def telegram(request):
    hash = request.GET.get('hash')
    if not hash:
        return render(request, 'artshow/bid_telegram.html', {
            'error': 'Telegram response has missing hash.'
        })

    secret_key = hashlib.sha256(artshow_settings.ARTSHOW_TELEGRAM_BOT_TOKEN.encode('utf-8'))
    data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(request.GET.items()) if k != 'hash')
    digest = hmac.new(secret_key.digest(), data_check_string.encode("utf-8"), hashlib.sha256)
    print(data_check_string)
    print(digest.hexdigest())
    print(hash)
    if digest.hexdigest() != hash:
        return render(request, 'artshow/bid_telegram.html', {
            'error': 'Invalid response from Telegram.'
        })

    auth_date = datetime.fromtimestamp(int(request.GET.get('auth_date', 0)),
                                       timezone.utc)
    if auth_date < now() - timedelta(minutes=5):
        return render(request, 'artshow/bid_telegram.html', {
            'error': 'Authentication expired.'
        })

    person = request.user.person
    person.telegram_chat_id = request.GET.get('id')
    person.telegram_username = request.GET.get('username')
    person.save()

    send_telegram_message(
        person.telegram_chat_id,
        render_to_string('artshow/telegram_welcome_message.txt', {
            'artshow_settings': artshow_settings,
        }))

    return render(request, 'artshow/bid_telegram.html', {
        'person': person,
    })
