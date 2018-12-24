from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Artist, Piece


@permission_required('artshow.is_artshow_staff')
def index(request):
    return render(request, 'artshow/workflows_index.html')


@permission_required('artshow.is_artshow_staff')
def printing(request):
    bid_sheets_query = Piece.objects.filter(status__in=(Piece.StatusNotInShow, Piece.StatusNotInShowLocked),
                                            bid_sheet_printing=Piece.PrintingNotPrinted)
    control_forms_query = Piece.objects.filter(status__in=(Piece.StatusNotInShow, Piece.StatusNotInShowLocked),
                                               control_form_printing=Piece.PrintingNotPrinted)
    bid_sheets_to_print_query = Piece.objects.filter(bid_sheet_printing=Piece.PrintingToBePrinted).order_by('artist__artistid', 'pieceid')
    control_forms_to_print_query = Piece.objects.filter(control_form_printing=Piece.PrintingToBePrinted).order_by('artist__artistid', 'pieceid')

    if request.method == "POST":
        if request.POST.get("lock_pieces"):
            bid_sheets_marked = bid_sheets_query.update(
                status=Piece.StatusNotInShowLocked,
                bid_sheet_printing=Piece.PrintingToBePrinted)
            control_forms_marked = control_forms_query.update(
                status=Piece.StatusNotInShowLocked,
                control_form_printing=Piece.PrintingToBePrinted)
            messages.info(request, "%d pieces have been marked for bid sheet printing, %d for control form printing" % (
                bid_sheets_marked, control_forms_marked))
            return redirect('.')
        elif request.POST.get("print_bid_sheets"):
            from . import bidsheets
            response = HttpResponse(content_type="application/pdf")
            bidsheets.generate_bidsheets(output=response, pieces=bid_sheets_to_print_query)
            messages.info(request, "Bid sheets printed.")
            return response

        elif request.POST.get("print_control_forms"):
            from . import bidsheets
            response = HttpResponse(content_type="application/pdf")
            bidsheets.generate_control_forms_for_pieces(output=response, pieces=control_forms_to_print_query)
            messages.info(request, "Control forms printed.")
            return response

        elif request.POST.get("bid_sheets_done"):
            pieces_marked = bid_sheets_to_print_query.update(bid_sheet_printing=Piece.PrintingPrinted)
            messages.info(request, "%d pieces marked as bid sheet printed" % pieces_marked)
            return redirect('.')

        elif request.POST.get("control_forms_done"):
            pieces_marked = control_forms_to_print_query.update(control_form_printing=Piece.PrintingPrinted)
            messages.info(request, "%d pieces marked as control form printed" % pieces_marked)
            return redirect('.')

    context = {
        'num_pieces_bid_sheet_unprinted': bid_sheets_query.count(),
        'num_pieces_control_form_unprinted': control_forms_query.count(),
        'num_bid_sheets_to_be_printed': bid_sheets_to_print_query.count(),
        'num_control_forms_to_be_printed': control_forms_to_print_query.count(),
        'num_bid_sheets_printed': Piece.objects.filter(bid_sheet_printing=Piece.PrintingPrinted).count(),
        'num_control_forms_printed': Piece.objects.filter(control_form_printing=Piece.PrintingPrinted).count(),
    }

    return render(request, 'artshow/workflows_printing.html', context)


class ArtistSearchForm(forms.Form):
    text = forms.CharField(label="Search Text")


@permission_required('artshow.is_artshow_staff')
def find_artist_checkin(request):
    search_executed = False
    if request.method == "POST":
        form = ArtistSearchForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data['text']
            query = (Q(person__name__icontains=text)
                     | Q(publicname__icontains=text))
            try:
                artistid = int(text)
                query = query | Q(artistid=artistid)
            except ValueError:
                pass
            artists = Artist.objects.filter(query)
            search_executed = True
        else:
            artists = []
    else:
        form = ArtistSearchForm()
        artists = []

    c = {"form": form, "artists": artists, "search_executed": search_executed}
    return render(request, 'artshow/workflows_artist_checkin_lookup.html', c)


class PieceForm(forms.ModelForm):
    print_item = forms.BooleanField(label='Print', initial=False, required=False)

    class Meta:
        model = Piece
        fields = (
            'print_item', 'pieceid', 'name', 'media', 'adult',
            'reproduction_rights_included', 'not_for_sale', 'min_bid',
            'buy_now',
        )
        widgets = {
            'pieceid': forms.TextInput(attrs={'size': 4}),
            'name': forms.TextInput(attrs={'size': 40}),
            'media': forms.TextInput(attrs={'size': 40}),
            'min_bid': forms.TextInput(attrs={'size': 5}),
            'buy_now': forms.TextInput(attrs={'size': 5}),
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.instance.id is not None:
            self.fields['print_item'].initial = True


PieceFormSet = inlineformset_factory(Artist, Piece, form=PieceForm,
                                     extra=3, can_delete=False)


@permission_required('artshow.is_artshow_staff')
def artist_checkin(request, artistid):
    artist = get_object_or_404(Artist, artistid=artistid)
    if request.method == 'POST':
        formset = PieceFormSet(request.POST,
                               queryset=artist.piece_set.order_by('pieceid'),
                               instance=artist)
        if formset.is_valid():
            formset.save()
            # Create a fresh formset for further edits.
            formset = PieceFormSet(queryset=artist.piece_set.order_by('pieceid'),
                                   instance=artist)
    else:
        formset = PieceFormSet(queryset=artist.piece_set.order_by('pieceid'),
                               instance=artist)

    c = {'artist': artist, 'formset': formset}
    return render(request, 'artshow/workflows_artist_checkin.html', c)


@permission_required('artshow.is_artshow_staff')
@require_POST
def artist_print_control_form(request, artistid):
    artist = get_object_or_404(Artist, artistid=artistid)
    formset = PieceFormSet(request.POST,
                           queryset=artist.piece_set.order_by('pieceid'),
                           instance=artist)
    if not formset.is_valid():
        c = {'artist': artist, 'formset': formset}
        return render(request, 'artshow/workflows_artist_checkin.html', c)
    formset.save()

    c = {
        'artists': [artist],
        'print': True,
        'redirect': reverse('artshow-workflow-artist-checkin',
                            kwargs={'artistid': artist.artistid}),
    }
    return render(request, 'artshow/control_form.html', c)


@permission_required('artshow.is_artshow_staff')
@require_POST
def artist_print_bid_sheets(request, artistid):
    artist = get_object_or_404(Artist, artistid=artistid)
    formset = PieceFormSet(request.POST,
                           queryset=artist.piece_set.order_by('pieceid'),
                           instance=artist)
    if not formset.is_valid():
        c = {'artist': artist, 'formset': formset}
        return render(request, 'artshow/workflows_artist_checkin.html', c)
    formset.save()

    pieces = []
    for form in formset:
        if 'print_item' in form.cleaned_data and form.cleaned_data['print_item']:
            pieces.append(form.instance)

    c = {
        'pieces': pieces,
        'print': True,
        'redirect': reverse('artshow-workflow-artist-checkin',
                            kwargs={'artistid': artist.artistid}),
    }
    return render(request, 'artshow/bid_sheets.html', c)


@permission_required('artshow.is_artshow_staff')
@require_POST
def artist_print_piece_stickers(request, artistid):
    artist = get_object_or_404(Artist, artistid=artistid)
    formset = PieceFormSet(request.POST,
                           queryset=artist.piece_set.order_by('pieceid'),
                           instance=artist)
    if not formset.is_valid():
        c = {'artist': artist, 'formset': formset}
        return render(request, 'artshow/workflows_artist_checkin.html', c)
    formset.save()

    pieces = []
    for form in formset:
        if 'print_item' in form.cleaned_data and form.cleaned_data['print_item']:
            pieces.append(form.instance)

    c = {
        'pieces': pieces,
        'print': True,
        'redirect': reverse('artshow-workflow-artist-checkin',
                            kwargs={'artistid': artist.artistid}),
    }
    return render(request, 'artshow/piece_stickers.html', c)
