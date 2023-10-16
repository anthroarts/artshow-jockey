from decimal import Decimal
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
from django.forms import HiddenInput, ModelChoiceField
from django.forms.formsets import formset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.urls import reverse
from .models import (
    Allocation, Artist, Location, Payment, Piece, Space, validate_space,
    validate_space_increments
)
from django import forms
from django.contrib.auth.decorators import login_required
from django.forms.models import inlineformset_factory
from django.http import HttpResponse
from django.contrib import messages
from .utils import artshow_settings
from . import square
from . import utils
import re
from django.conf import settings


EXTRA_PIECES = 5
Person = apps.get_model(settings.ARTSHOW_PERSON_CLASS)


def user_edits_allowable(view_func):
    def decorator(request, *args, **kwargs):
        if settings.ARTSHOW_SHUT_USER_EDITS:
            error = "The Art Show Administration has disallowed edits for the time being."
            return render(request, "artshow/manage_error.html", {'artshow_settings': artshow_settings,
                                                                 'error': error})
        return view_func(request, *args, **kwargs)
    return decorator


@login_required
def index(request):
    artists = Artist.objects.viewable_by(request.user)
    return render(request, "artshow/manage_index.html", {'artists': artists, 'artshow_settings': artshow_settings})


@login_required
def artist(request, artist_id):

    artist = get_object_or_404(Artist.objects.viewable_by(request.user), pk=artist_id)
    pieces = artist.piece_set.order_by("pieceid")
    payments = artist.payment_set.order_by("date", "id")
    payments_total = payments.aggregate(payments_total=Sum('amount'))['payments_total'] or Decimal(0)
    total_requested_cost, deduction_to_date, deduction_remaining = \
        artist.deduction_remaining_with_details()
    payments_total -= deduction_remaining

    allocations = artist.allocation_set.order_by("space__id")

    allocation_map = {a.space.pk: a for a in allocations}
    # Re-calculate the number of allocated spaces based on the assigned
    # locations.
    for a in allocations:
        a.allocated = 0.0

    locations = Location.objects.filter(Q(artist_1=artist) | Q(artist_2=artist))
    for l in locations:
        if l.type.pk in allocation_map:
            allocation_map[l.type.pk].allocated += 0.5 if l.space_is_split or l.half_space else 1.0

    can_edit_personal_details = not settings.ARTSHOW_SHUT_USER_EDITS and \
        (request.user == artist.person.user)
    can_edit_artist_details = can_edit_personal_details
    can_edit_piece_details = not settings.ARTSHOW_SHUT_USER_EDITS and \
        artist.grants_access_to(request.user, can_edit_pieces=True)
    can_edit_space_reservations = not settings.ARTSHOW_SHUT_USER_EDITS and \
        artist.grants_access_to(request.user, can_edit_spaces=True)

    return render(request, "artshow/manage_artist.html",
                  {'artist': artist, 'pieces': pieces, 'allocations': allocations,
                   'payments': payments, 'payments_total': payments_total,
                   'deduction_remaining': deduction_remaining,
                   'can_edit_personal_details': can_edit_personal_details,
                   'can_edit_artist_details': can_edit_artist_details,
                   'can_edit_piece_details': can_edit_piece_details,
                   'can_edit_space_reservations': can_edit_space_reservations,
                   'artshow_settings': artshow_settings})


class PieceForm(forms.ModelForm):
    class Meta:
        model = Piece
        fields = (
            'pieceid', 'name', 'media', 'other_artist', 'condition',
            'not_for_sale', 'adult', 'reproduction_rights_included', 'min_bid',
            'buy_now'
        )
        widgets = {
            'pieceid': forms.TextInput(attrs={'size': 4}),
            'name': forms.TextInput(attrs={'size': 40}),
            'media': forms.TextInput(attrs={'size': 40}),
            'min_bid': forms.TextInput(attrs={'size': 5}),
            'buy_now': forms.TextInput(attrs={'size': 5}),
        }


PieceFormSet = inlineformset_factory(Artist, Piece, form=PieceForm,
                                     extra=EXTRA_PIECES,
                                     can_delete=True,
                                     )


class DeleteConfirmForm(forms.Form):
    confirm_delete = forms.BooleanField(
        required=False,
        help_text="You are about to delete pieces. The information is not recoverable. Please confirm."
    )


@login_required
@user_edits_allowable
def pieces(request, artist_id):
    artist = get_object_or_404(Artist.objects.viewable_by(request.user), pk=artist_id)

    if not artist.grants_access_to(request.user, can_edit_pieces=True):
        error = "You do not have permissions to edit pieces for this artist."
        return render(request, "artshow/manage_error.html", {'artshow_settings': artshow_settings,
                                                             'error': error})

    # TODO create a custom filter/exclude in the model rather than checking for a status here.
    locked_pieces = artist.piece_set.exclude(status=Piece.StatusNotInShow).order_by("pieceid")
    editable_pieces = artist.piece_set.filter(status=Piece.StatusNotInShow).order_by("pieceid")

    # TODO things go badly if the status on a piece changes between the render, and the post
    if request.method == "POST":
        formset = PieceFormSet(request.POST, queryset=editable_pieces, instance=artist)
        delete_confirm_form = DeleteConfirmForm(request.POST)
        if formset.is_valid() and delete_confirm_form.is_valid():
            if not formset.deleted_forms or delete_confirm_form.cleaned_data['confirm_delete']:
                formset.save()
                messages.info(request, "Changes to piece details have been saved")
                return redirect('.')
    else:
        formset = PieceFormSet(queryset=editable_pieces, instance=artist)
        delete_confirm_form = DeleteConfirmForm()

    return render(request, "artshow/manage_pieces.html",
                  {'artist': artist, 'formset': formset, 'delete_confirm_form': delete_confirm_form,
                   'locked_pieces': locked_pieces, 'artshow_settings': artshow_settings})


def yesno(b):
    return "yes" if b else "no"


@login_required
def downloadcsv(request, artist_id):
    artist = get_object_or_404(Artist.objects.viewable_by(request.user), pk=artist_id)

    reduced_artist_name = re.sub('[^A-Za-z0-9]+', '', artist.artistname()).lower()
    filename = "pieces-" + reduced_artist_name + ".csv"

    field_names = ['pieceid', 'code', 'title', 'media', 'min_bid', 'buy_now', 'adult', 'not_for_sale']

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = "attachment; filename=" + filename

    c = utils.UnicodeCSVWriter(response)
    c.writerow(field_names)

    for p in artist.piece_set.all():
        c.writerow((p.pieceid, p.code, p.name, p.media, p.min_bid, p.buy_now, yesno(p.adult), yesno(p.not_for_sale)))

    return response


@login_required
def bid_sheets(request, artist_id):
    artist = get_object_or_404(Artist.objects.viewable_by(request.user),
                               pk=artist_id)

    return render(request, "artshow/bid_sheets.html",
                  {'artist': artist, 'pieces': artist.ordered_pieces()})


@login_required
def control_forms(request, artist_id):
    artist = get_object_or_404(Artist.objects.viewable_by(request.user),
                               pk=artist_id)

    return render(request, "artshow/control_form.html", {
        'artists': [artist],
        'check_in': True,
        'check_out': True,
    })


def requestspaceform_factory(artist):
    class RequestSpaceForm(forms.Form):
        space = ModelChoiceField(queryset=Space.objects.all(), widget=HiddenInput)
        requested = forms.DecimalField(validators=[validate_space])

        def clean_space(self):
            # We're going to use this to force a form to have initial data for this field.
            # so the template can go form.initial.space to get details on the space.
            space = self.cleaned_data['space']
            try:
                space.artist_allocation = space.allocation_set.get(artist=artist)
            except Allocation.DoesNotExist:
                space.artist_allocation = None
            self.initial['space'] = space
            return space

        def clean_requested(self):
            requested = self.cleaned_data['requested']
            try:
                validate_space_increments(requested, self.initial['space'].allow_half_spaces)
            except ValidationError:
                del self.cleaned_data['requested']
                raise
            return requested

    return RequestSpaceForm


@login_required
@user_edits_allowable
def spaces(request, artist_id):
    artist = get_object_or_404(Artist.objects.grants_access_to(request.user, can_edit_spaces=True), pk=artist_id)

    RequestSpaceForm = requestspaceform_factory(artist)
    RequestSpaceFormSet = formset_factory(RequestSpaceForm, extra=0)

    spaces = Space.objects.order_by('id')
    for s in spaces:
        try:
            s.artist_allocation = s.allocation_set.get(artist=artist)
            # Re-calculate the number of allocated spaces based on the assigned
            # locations.
            s.artist_allocation.allocated = 0.0
        except Allocation.DoesNotExist:
            s.artist_allocation = None
    spaces = [s for s in spaces if s.reservable is True or s.artist_allocation is not None]

    locations = Location.objects.filter(Q(artist_1=artist) | Q(artist_2=artist))
    space_map = {s.pk: s for s in spaces}
    for l in locations:
        if l.type.pk in space_map:
            s = space_map[l.type.pk]
            if s.artist_allocation is not None:
                s.artist_allocation.allocated += 0.5 if l.space_is_split or l.half_space else 1.0

    if request.method == "POST":
        formset = RequestSpaceFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                space = form.cleaned_data['space']
                requested = form.cleaned_data['requested']
                try:
                    allocation = Allocation.objects.get(artist=artist, space=space)
                except Allocation.DoesNotExist:
                    # If the Allocation didn't exist and the space is not reservable, then this should
                    # have not been possible. Just raise it as a error message and keep moving.
                    if not space.reservable:
                        messages.error(request, "%s is not reservable, and was removed from your request" % space)
                        continue
                    # Allocation doesn't exist, and we're not requesting any. Move on.
                    if requested == 0:
                        continue
                    # Allocation doesn't exist, and we want to reserve it. Create one.
                    allocation = Allocation(artist=artist, space=space)
                else:
                    # If the Allocation existed, the current allocated is 0, and the request is 0, then
                    # just delete the Allocation object.
                    if allocation.allocated == 0 and requested == 0:
                        allocation.delete()
                        continue
                allocation.requested = requested
                allocation.save()
            return redirect(reverse('artshow-manage-artist', args=(artist_id,)))
    else:
        formset = RequestSpaceFormSet(initial=[{'requested': s.artist_allocation.requested if s.artist_allocation is not None else 0,
                                                'space': s} for s in spaces])

    return render(request, "artshow/manage_spaces.html", {"artist": artist, "formset": formset,
                                                          "artshow_settings": artshow_settings})


class ArtistModelForm(forms.ModelForm):
    publicname = forms.CharField(label="Artist Name", required=False,
                                 help_text="The name we'll display to the public. "
                                           "Make this blank to use your real name")

    class Meta:
        model = Artist
        fields = ('publicname', 'website', 'mailin')


@login_required
@user_edits_allowable
def artist_details(request, artist_id):
    artist = get_object_or_404(Artist.objects.filter(person__user=request.user), pk=artist_id)

    if request.method == "POST":
        form = ArtistModelForm(request.POST, instance=artist)
        if form.is_valid():
            form.save()
            messages.info(request, "Changes to your artist details have been saved")
            return redirect(reverse('artshow-manage-artist', args=(artist_id,)))
    else:
        form = ArtistModelForm(instance=artist)

    return render(request, "artshow/manage_artist_details.html", {"artist": artist, "form": form,
                                                                  "artshow_settings": artshow_settings})


class PersonModelForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ('name', 'address1', 'address2', 'city', 'state', 'postcode', 'country', 'phone')


@login_required
@user_edits_allowable
def person_details(request, artist_id):
    artist = get_object_or_404(Artist.objects.filter(person__user=request.user), pk=artist_id)
    person = artist.person

    if request.method == "POST":
        form = PersonModelForm(request.POST, instance=person)
        if form.is_valid():
            form.save()
            messages.info(request, "Changes to your personal details have been saved")
            return redirect(reverse('artshow-manage-artist', args=(artist_id,)))
    else:
        form = PersonModelForm(instance=person)

    return render(request, "artshow/manage_person_details.html", {"person": person, "artist": artist,
                                                                  "form": form,
                                                                  "artshow_settings": artshow_settings})


class PaymentForm(forms.Form):
    amount = forms.DecimalField(required=True, max_digits=7, decimal_places=2)
    nonce = forms.CharField(required=False)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be above zero")
        return amount


@login_required
@user_edits_allowable
def make_payment(request, artist_id):
    artist = get_object_or_404(Artist.objects.viewable_by(request.user), pk=artist_id)
    total_requested_cost, deduction_to_date, deduction_remaining, payment_remaining = \
        artist.payment_remaining_with_details()

    payment_remaining = Decimal(payment_remaining).quantize(Decimal('1.00'))
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = Payment(artist=artist,
                              amount=form.cleaned_data["amount"],
                              payment_type_id=settings.ARTSHOW_PAYMENT_PENDING_PK,
                              description="",
                              date=now())

            transaction = square.charge(payment, form.cleaned_data["nonce"])
            if transaction:
                payment.payment_type_id = settings.ARTSHOW_PAYMENT_RECEIVED_PK
                payment.description = "Square " + transaction
                payment.save()
                return redirect(reverse("artshow-manage-payment-square",
                                args=(artist_id,)))
            else:
                form.add_error(None, "Failed to charge payment.")
    else:
        form = PaymentForm(initial={'amount': payment_remaining})

    context = {"form": form,
               "artist": artist,
               "allocations": artist.allocation_set.order_by("id"),
               "total_requested_cost": total_requested_cost,
               "deduction_to_date": deduction_to_date,
               "deduction_remaining": deduction_remaining,
               "account_balance": artist.balance(),
               "payment_remaining": payment_remaining,
               "sq_application_id": settings.ARTSHOW_SQUARE_APPLICATION_ID,
               "sq_location_id": settings.ARTSHOW_SQUARE_LOCATION_ID,
               }

    return render(request, "artshow/make_payment.html", context)


@login_required
def payment_made_mail(request, artist_id):
    artist = get_object_or_404(Artist.objects.viewable_by(request.user), pk=artist_id)
    return render(request, "artshow/payment_made_mail.html", {"artist": artist})


@login_required
def payment_made_square(request, artist_id):
    artist = get_object_or_404(Artist.objects.viewable_by(request.user), pk=artist_id)
    return render(request, "artshow/payment_made_square.html", {"artist": artist})
