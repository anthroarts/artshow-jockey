from io import StringIO
import subprocess
from django import forms
from django.apps import apps
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404, render, redirect, reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from formtools.wizard.views import CookieWizardView
from .conf import settings
from .forms import LongerTextInput
from .models import Bidder, BidderId
import logging
from .conf import _DISABLED as SETTING_DISABLED


Person = apps.get_model(settings.ARTSHOW_PERSON_CLASS)


logger = logging.getLogger(__name__)


class BasicsForm(forms.Form):
    name = forms.CharField(
        label="Legal name",
        max_length=100,
        help_text="Your legal first and last name. This should match your "
                  "identification.")
    reg_id = forms.CharField(
        label="Registration ID",
        max_length=20,
        help_text="The number on the front of your convention badge. It looks "
                  "like PR:1234 or 1234569, and may have fewer or more digits. "
                  "Enter the whole thing.")

    def clean_reg_id(self):
        reg_id = self.cleaned_data['reg_id']

        matched_people = Person.objects.filter(reg_id=reg_id)
        if BidderId.objects.filter(
                bidder__person__in=matched_people).exists():
            raise forms.ValidationError(
                "We think you have already been issued a Bidder ID. If "
                "this is unexpected, please see Staff immediately")

        return reg_id


class ContactForm(forms.Form):
    email = forms.CharField(
        label="E-mail address", max_length=100, required=True)
    phone = forms.CharField(
        label="Phone number", max_length=40, required=True)
    address1 = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Address line 1',
            'style': 'width: 292px'}))
    address2 = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Address line 2 (optional)',
            'style': 'width: 292px'}))
    city = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'City',
            'style': 'width: 140px'}))
    state = forms.CharField(
        max_length=40, required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'State',
            'style': 'width: 60px'}))
    postcode = forms.CharField(
        max_length=20, required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'ZIP code',
            'style': 'width: 76px'}))
    country = forms.CharField(
        max_length=40, required=False, empty_value='USA',
        widget=forms.TextInput(attrs={
            'placeholder': 'Country',
            'style': 'width: 292px'}))


class AtConContactForm(forms.Form):
    at_con_contact = forms.CharField(
        max_length=100, required=False,
        widget=LongerTextInput,
        help_text="If there is a better way to contact you at the convention, "
                  "such as a friend's cell phone or a hotel room number. "
                  "Please enter it here.")


@permission_required('artshow.is_artshow_kiosk')
def main(request):
    if request.method == "POST":
        basics_form = BasicsForm(request.POST)
        contact_form = ContactForm(request.POST)
        at_con_contact_form = AtConContactForm(request.POST)

        if basics_form.is_valid() and contact_form.is_valid() and at_con_contact_form.is_valid():
            p = Person(
                name=basics_form.cleaned_data['name'],
                reg_id=basics_form.cleaned_data['reg_id'],
                address1=contact_form.cleaned_data['address1'],
                address2=contact_form.cleaned_data['address2'],
                city=contact_form.cleaned_data['city'],
                state=contact_form.cleaned_data['state'],
                postcode=contact_form.cleaned_data['postcode'],
                country=contact_form.cleaned_data['country'],
                phone=contact_form.cleaned_data['phone'],
                email=contact_form.cleaned_data['email'],
            )

            b = Bidder(
                at_con_contact=at_con_contact_form.cleaned_data['at_con_contact']
            )

            p.save()
            b.person = p
            b.save()

            return redirect(reverse('artshow-bidderreg-final'))
    else:
        basics_form = BasicsForm()
        contact_form = ContactForm()
        at_con_contact_form = AtConContactForm()

    return render(request, "artshow/bidderreg_wizard.html",
                  {"basics_form": basics_form,
                   "contact_form": contact_form,
                   "at_con_contact_form": at_con_contact_form})


@permission_required('artshow.is_artshow_kiosk')
def final(request):
    return render(request, "artshow/bidderreg_final.html")


@permission_required('artshow.is_artshow_staff')
@xframe_options_sameorigin
def bidder_agreement(request, pk):
    bidder = get_object_or_404(Bidder, pk=pk)
    at_con_contact = bidder.at_con_contact
    if len(at_con_contact) == 0:
        at_con_contact = bidder.person.phone
    return render(request, "artshow/bidder_agreement.html", {
        'bidder': bidder,
        'at_con_contact': at_con_contact})
