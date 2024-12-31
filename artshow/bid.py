from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.timezone import now
from django import forms

from .models import Bid, Bidder, Piece
from .utils import artshow_settings

from datetime import datetime, timedelta
import hashlib
import hmac

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


@login_required(login_url=LOGIN_URL)
def index(request):
    try:
        bidder = Bidder.objects.get(person__user=request.user)

        pieces_won = []
        pieces_not_won = []
        pieces_in_voice_auction = []

        winning_bid_query = Bid.objects.filter(
            piece=OuterRef('pk'), invalid=False).order_by('-amount')[:1]
        pieces = Piece.objects.filter(bid__bidder=bidder).annotate(
            top_bidder=Subquery(winning_bid_query.values('bidder')),
            top_bid=Subquery(winning_bid_query.values('amount'))
        ).order_by('artist', 'code').distinct()

        for piece in pieces:
            if piece.status == Piece.StatusInShow and piece.voice_auction:
                pieces_in_voice_auction.append(piece)
            elif piece.status == Piece.StatusWon:
                if piece.top_bidder == bidder.pk:
                    pieces_won.append(piece)
                else:
                    pieces_not_won.append(piece)

        show_has_bids = Bid.objects.filter(invalid=False).exists()

        return render(request, "artshow/bid_index.html", {
            'bidder': bidder,
            'show_has_bids': show_has_bids,
            'pieces_won': pieces_won,
            'pieces_not_won': pieces_not_won,
            'pieces_in_voice_auction': pieces_in_voice_auction,
        })
    except Bidder.DoesNotExist:
        return redirect('artshow-bid-register')


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


def sha256(data):
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def hmac_sha256(key, message):
    return hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


@login_required(login_url=LOGIN_URL)
def telegram(request):
    hash = request.GET.get('hash')
    if not hash:
        return render(request, 'artshow/bid_telegram.html', {
            'error': 'Invalid response from Telegram.'
        })

    secret_key = sha256(artshow_settings.ARTSHOW_TELEGRAM_BOT_TOKEN)
    data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(request.GET.items()) if k != 'hash')
    if hash != hmac_sha256(secret_key, data_check_string):
        return render(request, 'artshow/bid_telegram.html', {
            'error': 'Invalid response from Telegram.'
        })

    auth_date = datetime.fromtimestamp(int(request.GET.get('auth_date', 0)))
    if auth_date < now() - timedelta(minutes=5):
        return render(request, 'artshow/bid_telegram.html', {
            'error': 'Authentication expired.'
        })

    person = request.user.person
    person.telegram_username = request.GET.get('username')
    person.save()

    return render(request, 'artshow/bid_telegram.html', {
        'person': person,
    })
