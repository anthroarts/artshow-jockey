from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django import forms
from .models import Bid, Bidder, Piece
from .utils import artshow_settings

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
            piece=OuterRef('pk'), invalid=False).order_by('-amount')
        pieces = Piece.objects.filter(bid__bidder=bidder).annotate(
            top_bidder=Subquery(winning_bid_query.values('bidder')[:1]),
            top_bid=Subquery(winning_bid_query.values('amount')[:1])).distinct()

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
            'artshow_settings': artshow_settings
        })
    except Bidder.DoesNotExist:
        return redirect('artshow-bid-register')


def login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(request.GET.get('next', reverse('artshow-bid')))

    return render(request, "artshow/bid_login.html", {'artshow_settings': artshow_settings})


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

    return render(request, "artshow/bid_register.html", {
        'artshow_settings': artshow_settings,
        'form': form,
    })
