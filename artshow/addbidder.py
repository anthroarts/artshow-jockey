# Artshow Jockey
# Copyright (C) 2009, 2010 Chris Cogdon
# See file COPYING for licence details
from django.apps import apps
from django.contrib import messages
from django.db.models import Q
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404, render, redirect
from .models import Bidder, BidderId, Piece, Bid
from django import forms
from django.core.exceptions import ValidationError
from . import mod11codes
import re
from django.forms.formsets import formset_factory
from django.contrib.auth.decorators import permission_required
from .conf import settings

BIDDERS_PER_PAGE = 10
BIDS_PER_PAGE = 10
Person = apps.get_model(settings.ARTSHOW_PERSON_CLASS)


def mod11check(value):
    if settings.ARTSHOW_BIDDERID_MOD11_OFFSET is None:
        return
    try:
        mod11codes.check(value, offset=settings.ARTSHOW_BIDDERID_MOD11_OFFSET)
    except (mod11codes.CheckDigitError, ValueError):
        raise ValidationError("Not a valid code")


class BidderAddForm(forms.Form):

    bidderid = forms.CharField(max_length=8, validators=[mod11check])
    name = forms.CharField(max_length=100)
    regid = forms.CharField(max_length=10)


BidderAddFormSet = formset_factory(BidderAddForm, extra=BIDDERS_PER_PAGE)


@permission_required('artshow.add_bidder')
def bulk_add(request):
    if request.method == "POST":
        formset = BidderAddFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                bidderid = form.cleaned_data.get('bidderid')
                if not bidderid:
                    continue
                name = form.cleaned_data['name']
                regid = form.cleaned_data['regid']
                person = Person(name=name, reg_id=regid)
                person.save()
                bidder = Bidder(person=person)
                bidder.save()
                bidderid = BidderId(id=bidderid, bidder=bidder)
                bidderid.save()
            return redirect('.')

    else:
        formset = BidderAddFormSet()
    return render(request, 'artshow/bidderbulkadd.html', dict(formset=formset))


class BidAddForm (forms.Form):

    piece = forms.CharField(max_length=8)
    bidder = forms.CharField(max_length=8, required=False, validators=[mod11check])
    TYPE_CHOICES = (
        ('nobids', 'No Bids'),
        ('normal', 'Normal Bid'),
        ('buynow', 'Buy Now'),
        ('auction', 'Auction'),
        ('nfs', 'Not For Sale'),
        ('', "Clear"),
    )
    type = forms.ChoiceField(choices=TYPE_CHOICES, widget=forms.RadioSelect)
    amount = forms.IntegerField(required=False)

    piece_code_1 = re.compile(r"\s*(?P<artist_id>\d+)-(?P<piece_id>\d+)\s*$")
    piece_code_2 = re.compile(r"\s*[Aa](?P<artist_id>\d+)[Pp](?P<piece_id>\d+)\s*$")

    def clean_piece(self):
        piece_code = self.cleaned_data['piece']
        if not piece_code:
            return None
        mo = self.piece_code_1.match(piece_code)
        if not mo:
            mo = self.piece_code_2.match(piece_code)
        if not mo:
            raise forms.ValidationError("Not in known format")
        artist_id = mo.group('artist_id')
        piece_id = mo.group('piece_id')
        try:
            piece = Piece.objects.get(artist__artistid=artist_id, pieceid=piece_id)
        except Piece.DoesNotExist:
            raise forms.ValidationError("Piece does not exist")
        return piece

    def clean_bidder(self):
        bidder_code = self.cleaned_data['bidder']
        if not bidder_code:
            return None
        try:
            bidder = Bidder.objects.get(bidderid__id=bidder_code)
        except Bidder.DoesNotExist:
            raise forms.ValidationError("Bidder does not exist")
        return bidder

    def clean(self):
        if self._errors:
            return self.cleaned_data

        cleaned_data = super(BidAddForm, self).clean()
        bidder = cleaned_data['bidder']
        type = cleaned_data['type']
        choices = dict(self.TYPE_CHOICES)
        type_text = choices[type]
        amount = cleaned_data['amount']
        piece = cleaned_data['piece']

        if type in ('nobids', 'nfs'):
            if bidder:
                self._errors['bidder'] = self.error_class(["Bidder not permitted for type \"%s\"" % type_text])
                del cleaned_data['bidder']
                return cleaned_data
            if amount:
                self._errors['amount'] = self.error_class(["Amount not permitted for type \"%s\"" % type_text])
                del cleaned_data['amount']
                return cleaned_data
        else:
            if not bidder:
                self._errors['bidder'] = self.error_class(["Bidder required for type \"%s\"" % type_text])
                del cleaned_data['type']
                return cleaned_data
            if not amount:
                self._errors['amount'] = self.error_class(["Amount required for type \"%s\"" % type_text])
                del cleaned_data['amount']
                return cleaned_data

        if bidder is not None:
            try:
                bid = Bid.objects.get(bidder=bidder, amount=amount, piece=piece, buy_now_bid=(type == 'buynow'))
            except Bid.DoesNotExist:
                bid = Bid(bidder=bidder, amount=amount, piece=piece, buy_now_bid=(type == 'buynow'))
                bid.validate()
                bid.save()
            cleaned_data['bid'] = bid

        return cleaned_data


BidAddFormSet = formset_factory(BidAddForm, extra=BIDS_PER_PAGE)


class BidAddOptionsForm (forms.Form):

    STAGE_CHOICES = (
        ('mid', "Before close. Bids, or lack of, not counted as final."),
        ('close', "After close, before Voice Auction. Non-Voice Auction bids counted as final."),
        ('final', "After close and Voice Auction. All bids counted as final."),
    )

    stage = forms.ChoiceField(choices=STAGE_CHOICES, widget=forms.RadioSelect)


def finalize_bid(stage, piece, bid_type):

    assert stage in ('mid', 'close', 'final')
    assert bid_type in ('nobids', 'normal', 'buynow', 'auction')

    if bid_type == 'auction':
        # If the piece was already set voice_auction, leave it that way.
        piece.voice_auction = True

    if stage in ('close', 'final'):
        piece.bidsheet_scanned = True

    if (piece.status == Piece.StatusInShow
        and (stage == 'final'
             or (stage == 'close' and bid_type in ('normal', 'buynow')))):
        piece.status = Piece.StatusWon

    if (piece.status == Piece.StatusInShow and piece.voice_auction
            and stage == 'final' and bid_type == 'nobids'):
        piece.status = Piece.StatusWon

    piece.save()


@permission_required('artshow.add_bid')
@atomic
def bid_bulk_add(request):

    if request.method == "POST":
        formset = BidAddFormSet(request.POST, prefix="bids")
        optionsform = BidAddOptionsForm(request.POST, prefix="options")
        if optionsform.is_valid() and formset.is_valid():
            stage = optionsform.cleaned_data['stage']
            num_pieces_processed = 0
            for form in formset:
                bid = form.cleaned_data.get('bid')
                bid_type = form.cleaned_data.get('type')
                piece = form.cleaned_data.get('piece')
                if bid is not None:
                    bid.save()
                if piece is not None:
                    finalize_bid(stage, piece, bid_type)
                    num_pieces_processed += 1
            messages.info(request, "%d entries processed" % num_pieces_processed)
            return redirect('.')
    else:
        formset = BidAddFormSet(prefix="bids")
        optionsform = BidAddOptionsForm(prefix="options")
    return render(request, 'artshow/bidbulkadd.html', dict(formset=formset, optionsform=optionsform))


class BidderSearchForm(forms.Form):
    text = forms.CharField(label="Search Text")


@permission_required('artshow.add_bidder_id')
def find_bidder(request):
    search_executed = False
    if request.method == "POST":
        form = BidderSearchForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data['text']
            bidders = Bidder.objects.filter(Q(person__name__icontains=text)
                                            | Q(person__reg_id__icontains=text)
                                            | Q(bidderid__id=text)).distinct()
            search_executed = True
        else:
            bidders = []
    else:
        form = BidderSearchForm()
        bidders = []

    c = {"form": form, "bidders": bidders, "search_executed": search_executed}
    return render(request, 'artshow/workflows_find_bidder.html', c)


def is_valid_and_unassigned(value):
    mod11check(value)
    try:
        bidder_id = BidderId.objects.get(id=value)
        if bidder_id.bidder:
            raise ValidationError("ID has already been assigned to a bidder")
    except BidderId.DoesNotExist:
        raise ValidationError("ID is not in the database")


class BidderIdAddForm(forms.Form):
    bidderid = forms.CharField(max_length=8,
                               validators=[is_valid_and_unassigned])


BidderIdAddFormSet = formset_factory(BidderIdAddForm)


@permission_required('artshow.is_artshow_staff')
def bidder_detail(request, pk):
    bidder = get_object_or_404(Bidder, pk=pk)

    if request.method == 'POST':
        formset = BidderIdAddFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                bidder_id = BidderId.objects.get(id=form.cleaned_data['bidderid'])
                bidder_id.bidder = bidder
                bidder_id.save()
            # Clear the form before rendering the results page.
            formset = BidderIdAddFormSet()
    else:
        formset = BidderIdAddFormSet()

    c = {'formset': formset, 'bidder': bidder}
    return render(request, 'artshow/workflows_bidder_detail.html', c)
