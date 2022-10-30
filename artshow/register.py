from django import forms
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .conf import settings
from .models import Artist
from django.shortcuts import redirect, render
from .forms import ArtistRegisterForm, LongerTextInput

Person = apps.get_model(settings.ARTSHOW_PERSON_CLASS)
User = get_user_model()


class AgreementForm(forms.Form):
    electronic_signature = \
        forms.CharField(required=True,
                        help_text="You must read and agree to our <a href=\"%s\" target=\"_blank\">"
                                  "Artist Agreement</a>. "
                                  "Please type in your full name here as your \"electronic signature\"." %
                                  settings.ARTSHOW_ARTIST_AGREEMENT_URL,
                        widget=LongerTextInput)


@login_required
def main(request):
    if settings.ARTSHOW_SHUT_USER_EDITS:
        return render(request, "artshow/registration_closed.html")

    if request.method == "POST":
        artist_form = ArtistRegisterForm(request.POST)
        agreement_form = AgreementForm(request.POST)
        if artist_form.is_valid():
            artist = Artist(person=request.user.person, publicname=artist_form.cleaned_data.get('artist_name', ''))
            artist.save()

            return redirect('artshow-manage-artist', artist_id=artist.artistid)
    else:
        artist_form = ArtistRegisterForm()
        agreement_form = AgreementForm()

    return render(request, "artshow/manage_register_main.html",
                  {"artist_form": artist_form,
                   "agreement_form": agreement_form})
