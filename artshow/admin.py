# Artshow Jockey
# Copyright (C) 2009, 2010 Chris Cogdon
# See file COPYING for licence details
import datetime
import decimal
import smtplib

from ajax_select import make_ajax_form
from ajax_select.admin import AjaxSelectAdmin, AjaxSelectAdminTabularInline
from ajax_select.fields import AutoCompleteSelectField
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Max, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html

from . import email1
from . import processbatchscan
from .models import (
    Agent, Allocation, Artist, BatchScan, Bid, Bidder, BidderId, Checkoff,
    ChequePayment, EmailSignature, EmailTemplate, Invoice, InvoiceItem,
    InvoicePayment, Payment, PaymentType, Piece, Space
)

User = get_user_model()


class AgentForm(forms.ModelForm):
    person = AutoCompleteSelectField('person', required=True)


class AgentInline(AjaxSelectAdminTabularInline):
    # TODO Ajax selects only works on forms visible at ready time.
    # Need to trigger 'init-autocomplete' each time "Add Another" is pressed.
    form = make_ajax_form(Agent,
                          {'person': 'person'},
                          show_help_text=True)
    model = Agent
    extra = 1


class AllocationInlineForm(forms.ModelForm):
    class Meta:
        model = Allocation
        fields = ('artist', 'space', 'requested', 'allocated')
        widgets = {
            'requested': forms.TextInput(attrs={'size': 6}),
            'allocated': forms.TextInput(attrs={'size': 6}),
        }


class AllocationInline(admin.TabularInline):
    model = Allocation
    extra = 1
    form = AllocationInlineForm


class PieceInlineForm(forms.ModelForm):
    class Meta:
        model = Piece
        fields = ("pieceid", "name", "media", "adult", "not_for_sale", "min_bid", "buy_now", "location",
                  "voice_auction", "status")
        widgets = {
            'pieceid': forms.TextInput(attrs={'size': 3}),
            'media': forms.TextInput(attrs={'size': 8}),
            'location': forms.TextInput(attrs={'size': 4}),
            'min_bid': forms.TextInput(attrs={'size': 6}),
            'buy_now': forms.TextInput(attrs={'size': 6}),
            'invoice_price': forms.TextInput(attrs={'size': 6}),
        }


class PieceInline(admin.TabularInline):
    form = PieceInlineForm
    fields = ("pieceid", "name", "media", "adult", "not_for_sale", "min_bid", "buy_now", "location", "voice_auction",
              "status")
    model = Piece
    extra = 5
    ordering = ('pieceid',)


# class ProductInline ( admin.TabularInline ):
#     fields = ("productid", "name", "adult", "price", "location")
#     model = Product
#     extra = 1
#     ordering = ('productid',)

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1


def send_password_reset_email(artist, user, subject, body_template):
    from django.utils.http import int_to_base36
    from django.contrib.auth.tokens import default_token_generator

    c = {
        'artist': artist,
        'user': user,
        'uid': int_to_base36(user.id),
        'token': default_token_generator.make_token(user),
    }
    body = email1.make_email2(c, body_template)
    send_mail(subject, body, settings.ARTSHOW_EMAIL_SENDER, [user.email], fail_silently=False)


class ArtistForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        if 'instance' not in kwargs:
            kwargs.setdefault('initial', {})
            kwargs['initial']['artistid'] = \
                (Artist.objects.aggregate(artistid=Max('artistid')).get('artistid', 0) or 0) + 1
        super(ArtistForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Artist
        fields = (
            'artistid', 'person', 'publicname', 'website', 'mailin',
            'mailback_instructions', 'attending', 'reservationdate', 'notes',
            'spaces', 'checkoffs', 'payment_to'
        )

    person = AutoCompleteSelectField('person', required=True)
    payment_to = AutoCompleteSelectField('person', required=False)


class ArtistAdmin(AjaxSelectAdmin):
    form = ArtistForm
    list_display = ('person_name', 'publicname', 'artistid', 'person_clickable_email', 'requested_spaces',
                    'allocated_spaces', 'piece_count')
    list_filter = ('mailin', 'person__country', 'checkoffs')
    search_fields = ('person__name', 'publicname', 'person__email', 'notes', 'artistid')
    fields = ['artistid', 'person', 'publicname', 'website', ('reservationdate', 'attending'),
              ('mailin', 'mailback_instructions'), 'notes', 'checkoffs', 'payment_to']
    inlines = [AgentInline, AllocationInline, PieceInline, PaymentInline]

    def requested_spaces(self, artist):
        return ", ".join("%s:%s" % (al.space.shortname, al.requested) for al in artist.allocation_set.all())

    def allocated_spaces(self, artist):
        return ", ".join("%s:%s" % (al.space.shortname, al.allocated) for al in artist.allocation_set.all())

    def piece_count(self, artist):
        return artist.piece_set.count()

    piece_count.short_description = "pieces"

    def person_name(self, artist):
        return artist.person.name

    person_name.short_description = "name"

    def person_clickable_email(self, artist):
        return artist.person.clickable_email()

    person_clickable_email.short_description = "email"
    person_clickable_email.allow_tags = True

    def send_email(self, request, queryset):
        opts = self.model._meta
        app_label = opts.app_label
        emails = []
        template_id = None
        signature_id = None
        if request.POST.get('post'):
            template_id = request.POST.get('template')
            signature_id = request.POST.get('signature')
            if not template_id:
                messages.error(request, "Please select a template")
            else:
                template_id = int(template_id)
                signature_id = int(signature_id or 0)
                selected_template = EmailTemplate.objects.get(pk=template_id)
                signature = EmailSignature.objects.get(pk=signature_id).signature if signature_id else ""
                if request.POST.get('send_email'):
                    for a in queryset:
                        email = a.person.email
                        body = email1.make_email(a, selected_template.template, signature)
                        try:
                            send_mail(selected_template.subject, body, settings.ARTSHOW_EMAIL_SENDER, [email],
                                      fail_silently=False)
                            self.message_user(request, "Mail to %s succeeded" % email)
                        except smtplib.SMTPException as x:
                            # Note: ModelAdmin message_user only supports sending info-level messages.
                            messages.error(request, "Mail to %s failed: %s" % (email, x))
                    return None
                else:
                    for a in queryset:
                        emails.append({'to': a.person.email,
                                       'body': email1.make_email(a, selected_template.template, signature)})
        templates = EmailTemplate.objects.all()
        signatures = EmailSignature.objects.all()
        context = {
            "title": "Send E-mail to Artists",
            "queryset": queryset,
            "opts": opts,
            # "root_path": self.admin_site.root_path,
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "templates": templates,
            "signatures": signatures,
            "emails": emails,
            "template_id": template_id,
            "signature_id": signature_id,
        }
        return render(request, "admin/email_selected_confirmation.html", context)

    send_email.short_description = "Send E-mail"

    def print_bidsheets(self, request, queryset):
        pieces = Piece.objects.filter(artist__in=queryset) \
                      .order_by('artist__artistid', 'pieceid')
        return render(request, 'artshow/bid_sheets.html',
                      {'pieces': pieces})

    print_bidsheets.short_description = "Print Bid Sheets"

    def print_mailing_labels(self, request, queryset):
        from . import bidsheets

        response = HttpResponse(content_type="application/pdf")
        bidsheets.generate_mailing_labels(output=response, artists=queryset)
        self.message_user(request, "Mailing labels printed.")
        return response

    print_mailing_labels.short_description = "Print Mailing Labels"

    def print_control_forms(self, request, artists):
        return render(request, 'artshow/control_form.html',
                      {'artists': artists})

    print_control_forms.short_description = "Print Control Forms"

    def print_piece_stickers(self, request, artists):
        pieces = Piece.objects.filter(artist__in=artists) \
                      .order_by('artist', 'pieceid')
        return render(request, 'artshow/piece_stickers.html',
                      {'pieces': pieces})

    print_piece_stickers.short_description = "Print Piece Stickers"

    def apply_space_fees(self, request, artists):
        payment_type = PaymentType.objects.get(pk=settings.ARTSHOW_SPACE_FEE_PK)
        for a in artists:
            Payment.objects.filter(artist=a, payment_type=payment_type).delete()
            total = 0
            for alloc in a.allocation_set.all():
                total += alloc.space.price * alloc.allocated
            if total > 0:
                allocated_spaces_str = ", ".join(
                    "%s:%s" % (al.space.shortname, al.allocated) for al in a.allocation_set.all())
                payment = Payment(artist=a, amount=-total, payment_type=payment_type, description=allocated_spaces_str,
                                  date=datetime.datetime.now())
                payment.save()

    def apply_winnings_and_commission(self, request, artists):
        pt_winning = PaymentType.objects.get(pk=settings.ARTSHOW_SALES_PK)
        pt_commission = PaymentType.objects.get(pk=settings.ARTSHOW_COMMISSION_PK)
        for a in artists:
            Payment.objects.filter(artist=a, payment_type__in=(pt_winning, pt_commission)).delete()
            total_winnings = 0
            total_pieces = 0
            pieces_with_bids = 0
            for piece in a.piece_set.all():
                if piece.status != Piece.StatusNotInShow:
                    total_pieces += 1
                try:
                    top_bid = piece.top_bid()
                    total_winnings += top_bid.amount
                    pieces_with_bids += 1
                except Bid.DoesNotExist:
                    pass
            commission = total_winnings * decimal.Decimal(settings.ARTSHOW_COMMISSION)
            if total_pieces > 0:
                payment = Payment(artist=a, amount=total_winnings,
                                  payment_type=pt_winning,
                                  description="%d piece%s, %d with bid%s" % (
                                      total_pieces,
                                      total_pieces != 1 and "s" or "",
                                      pieces_with_bids,
                                      pieces_with_bids != 1 and "s" or ""),
                                  date=datetime.datetime.now())
                payment.save()
            if commission > 0:
                payment = Payment(artist=a, amount=-commission, payment_type=pt_commission,
                                  description="%s%% of sales" % (decimal.Decimal(settings.ARTSHOW_COMMISSION) * 100),
                                  date=datetime.datetime.now())
                payment.save()

    # noinspection PyUnusedLocal
    def create_cheques(self, request, artists):
        pt_paymentsent = PaymentType.objects.get(pk=settings.ARTSHOW_PAYMENT_SENT_PK)
        for a in artists:
            balance = a.payment_set.aggregate(balance=Sum('amount'))['balance']
            if balance > 0:
                chq = ChequePayment(artist=a, payment_type=pt_paymentsent, amount=-balance,
                                    date=datetime.datetime.now())
                chq.clean()
                chq.save()

    # noinspection PyUnusedLocal
    def allocate_spaces(self, request, artists):
        artists = artists.order_by('reservationdate', 'artistid')
        spaces_remaining = {}
        for space in Space.objects.all():
            spaces_remaining[space.id] = space.remaining()
        for artist in artists:
            for alloc in artist.allocation_set.all():
                needed = alloc.requested - alloc.allocated
                to_allocate = min(needed, spaces_remaining[alloc.space.id])
                if to_allocate > 0:
                    alloc.allocated += to_allocate
                    spaces_remaining[alloc.space.id] -= to_allocate
                    alloc.save()

    def create_management_users(self, request, artists):
        opts = self.model._meta
        app_label = opts.app_label
        template_id = None
        if request.POST.get('post'):
            template_id = request.POST.get('template')
            if template_id:
                selected_template = EmailTemplate.objects.get(pk=template_id)
            else:
                selected_template = None
            # TODO this will not work if Person doesn't have a 'user' field that is the user model.
            for artist in artists:
                if artist.person.user:
                    messages.warning(request, "Artist %s already has a login user %s" % (artist, artist.person.user))
                    continue

                artist_email = artist.person.email
                if not artist_email:
                    messages.warning(request, "Artist %s does not have an email address." % artist)
                    continue

                try:
                    User.objects.get(username=artist_email)
                except User.DoesNotExist:
                    pass
                else:
                    messages.warning(request,
                                     "Artist %s has email address %s, "
                                     "but there is already a user with that "
                                     "address as a login." % (
                                         artist, artist_email))
                    continue

                user = User(username=artist_email, email=artist_email, first_name=artist.person.name, password='')
                user.set_unusable_password()
                user.save()
                artist.person.user = user
                artist.person.save()
                messages.info(request, "Artist %s has a login created" % artist)

                if selected_template:
                    try:
                        send_password_reset_email(artist, user, selected_template.subject,
                                                  selected_template.template)
                        self.message_user(request, "Mail to %s succeeded." % artist_email)
                    except smtplib.SMTPException as x:
                        # Note: ModelAdmin message_user only supports sending info-level messages.
                        messages.error(request, "Mail to %s failed: %s" % (artist_email, x))
            return None
        templates = EmailTemplate.objects.all()
        context = {
            "title": "Create Management Users",
            "queryset": artists,
            "opts": opts,
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "templates": templates,
            "template_id": template_id,
        }
        return render(request, "admin/create_management_users.html", context)

    create_management_users.short_description = "Create Management Users"

    actions = ('send_email', 'print_bidsheets', 'print_control_forms', 'print_mailing_labels', 'apply_space_fees',
               'apply_winnings_and_commission', 'create_cheques', 'allocate_spaces', 'create_management_users',
               'print_piece_stickers')
    filter_horizontal = ('checkoffs',)


admin.site.register(Artist, ArtistAdmin)


class SpaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'shortname', 'price', 'reservable', 'available', 'allocated', 'remaining', 'waiting')
    list_editable = ('reservable', 'available')


admin.site.register(Space, SpaceAdmin)


class PieceBidInline(admin.TabularInline):
    model = Bid
    raw_id_fields = ('bidder', )
    extra = 1


class PieceAdmin(admin.ModelAdmin):
    def clear_won_status(self, request, pieces):
        pieces.filter(status=Piece.StatusWon).update(status=Piece.StatusInShow,
                                                     voice_auction=False)
        self.message_user(request, "Pieces marked as 'Won' have been returned to 'In Show'.")

    def apply_won_status(self, request, pieces):
        # This code is duplicated in the management code
        for p in pieces.filter(status=Piece.StatusInShow):
            bid_count = p.bid_set.exclude(invalid=True).count()
            if bid_count > 0:
                p.voice_auction = bid_count >= 6
                if not p.voice_auction:
                    p.status = Piece.StatusWon
                p.save()
        self.message_user(request, "Pieces with bids marked as 'In Show' have been marked 'Won' or sent to voice auction.")

    def apply_returned_status(self, request, pieces):
        pieces.filter(status=Piece.StatusInShow).update(status=Piece.StatusReturned)
        self.message_user(request, "Pieces marked as 'In Show' have been marked 'Returned'.")

    def print_bidsheets(self, request, queryset):
        return render(request, 'artshow/bid_sheets.html',
                      {'pieces': queryset})

    print_bidsheets.short_description = "Print Bid Sheets"

    def print_piece_stickers(self, request, queryset):
        return render(request, 'artshow/piece_stickers.html',
                      {'pieces': queryset})

    print_piece_stickers.short_description = "Print Piece Stickers"

    def clickable_artist(self, obj):
        return format_html('<a href="{}">{}</a>',
                           reverse('admin:artshow_artist_change',
                                   args=(obj.artist.pk,)),
                           obj.artist.artistname())

    clickable_artist.allow_tags = True
    clickable_artist.short_description = "artist"

    def clickable_invoice(self, obj):
        return format_html('<a href="{}">{}</a>',
                           reverse('admin:artshow_invoice_change',
                                   args=(obj.invoice.id,)),
                           obj.invoice)

    clickable_invoice.allow_tags = True
    clickable_invoice.short_description = "invoice"

    def top_bid(self, obj):
        return obj.bid_set.exclude(invalid=True).order_by('-amount')[0:1].get().amount

    def top_bid_detail(self, obj):
        top_bid = obj.bid_set.exclude(invalid=True).order_by('-amount')[0:1].get()
        return "$%s by %s" % (top_bid.amount, top_bid.bidder)

    top_bid_detail.short_description = "Top bid"

    def invoice_item_detail(self, obj):
        return str(obj.invoiceitem)

    invoice_item_detail.short_description = "invoice"

    def min_bid_x(self, obj):
        if obj.not_for_sale or obj.min_bid is None:
            return "NFS"
        else:
            return obj.min_bid

    min_bid_x.short_description = "min bid"

    def buy_now_x(self, obj):
        if obj.buy_now is None:
            return "N/A"
        else:
            return obj.buy_now

    buy_now_x.short_description = "buy now"
    list_filter = ('adult', 'not_for_sale', 'voice_auction', 'status')
    search_fields = ('=code', '=artist__artistid', 'name', '=location', 'artist__person__name', 'artist__publicname')
    list_display = (
        'code', 'clickable_artist', 'name', 'adult', 'min_bid_x', 'buy_now_x',
        'location', 'voice_auction', 'status', 'top_bid', 'updated')
    list_editable = ('status',)
    inlines = [PieceBidInline]
    # raw_id_fields = ( 'invoice', )
    # TODO put 'invoiceitem' back into the list. Waiting on bug #16433
    fields = (
        'artist', 'pieceid', 'name', 'media', 'other_artist', 'condition',
        ('not_for_sale', 'adult', 'min_bid', 'buy_now'),
        ('status', 'location'),
        ('voice_auction', 'order'),
        'top_bid_detail', 'invoice_item_detail', 'updated',
        ('bid_sheet_printing', 'control_form_printing', 'bidsheet_scanned'),
    )
    raw_id_fields = ('artist', )
    readonly_fields = ('top_bid_detail', 'invoice_item_detail', 'updated')
    actions = ('clear_scanned_flag', 'set_scanned_flag', 'clear_won_status',
               'apply_won_status', 'apply_returned_status', 'print_bidsheets',
               'print_piece_stickers')


admin.site.register(Piece, PieceAdmin)

# admin.site.register(Product)


class BidderIdInline(admin.TabularInline):
    model = BidderId


class BidderBidInline(admin.TabularInline):
    model = Bid
    fields = ('piece', 'amount', 'buy_now_bid', 'invalid')
    raw_id_fields = ('piece', )


class BidderAdmin(AjaxSelectAdmin):
    form = make_ajax_form(Bidder, {'person': 'person'})

    def bidder_ids(self, obj):
        return ", ".join([bidderid.id for bidderid in obj.bidderid_set.all()])

    bidder_ids.short_description = "bidder IDs"

    def person_name(self, bidder):
        return bidder.person.name

    person_name.short_description = "name"

    def person_reg_id(self, bidder):
        return bidder.person.reg_id

    person_reg_id.short_description = "reg ID"

    def person_clickable_email(self, bidder):
        return bidder.person.clickable_email()

    person_clickable_email.allow_tags = True
    person_clickable_email.short_description = "email"

    # TODO, add mailing_label back in once we figure out how to do it for bidders and artists uniformly
    list_display = ('person_name', 'person_reg_id', 'bidder_ids', 'person_clickable_email')
    search_fields = ('person__name', 'person__reg_id', 'bidderid__id')
    fields = ["person", "at_con_contact", "notes"]
    inlines = [BidderIdInline, BidderBidInline]


admin.site.register(Bidder, BidderAdmin)


class BidderIdAdmin(AjaxSelectAdmin):
    ordering = ('id',)
    list_display = ('id', 'bidder')
    actions = ('print_bid_stickers',)
    form = make_ajax_form(BidderId, {'bidder': 'bidder'})

    def print_bid_stickers(self, request, queryset):
        bidder_ids = queryset
        if queryset.count() == 1:
            bidder_ids = [queryset.first()] * 4
        elif queryset.count() == 2:
            bidder_ids = [queryset[0]] * 2 + [queryset[1]] * 2
        elif queryset.count() % 4 != 0:
            messages.error(request, "Select 1, 2 or a multiple of 4 bidder IDs.")
            return

        return render(request, "artshow/bid_stickers.html",
                      {'bidder_ids': bidder_ids,
                       'range': list(range(15))})


admin.site.register(BidderId, BidderIdAdmin)


class EmailTemplateAdmin(admin.ModelAdmin):
    save_as = True


admin.site.register(EmailTemplate, EmailTemplateAdmin)


admin.site.register(EmailSignature)


class PaymentAdmin(admin.ModelAdmin):
    def clickable_artist(self, obj):
        return format_html('<a href="{}">{}</a>',
                           reverse('admin:artshow_artist_change',
                                   args=(obj.artist.pk,)),
                           str(obj.artist))
    clickable_artist.allow_tags = True
    clickable_artist.short_description = "artist"

    list_display = ('id', 'clickable_artist', 'amount', 'payment_type', 'description', 'date')
    list_filter = ('payment_type', )
    date_hierarchy = 'date'
    raw_id_fields = ('artist', )


admin.site.register(Payment, PaymentAdmin)

admin.site.register(PaymentType)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    # fields = ( 'piece', 'top_bid', 'price', )
    fields = ('piece', 'price', )
    raw_id_fields = ('piece', )
    # read_only_fields = ( 'top_bid', )


class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment


class InvoiceAdmin(admin.ModelAdmin):
    def bidder_name(self, obj):
        return obj.payer.name()

    def num_pieces(self, obj):
        return obj.invoiceitem_set.count()

    raw_id_fields = ('payer', )
    list_display = ('id', 'bidder_name', 'num_pieces', 'total_paid')
    search_fields = ('id', 'payer__person__name')
    inlines = [InvoiceItemInline, InvoicePaymentInline]


admin.site.register(Invoice, InvoiceAdmin)


class BidAdmin(admin.ModelAdmin):
    raw_id_fields = ("bidder", "piece")


admin.site.register(Bid, BidAdmin)


class CheckoffAdmin(admin.ModelAdmin):
    list_display = ('name', 'shortname')


admin.site.register(Checkoff, CheckoffAdmin)


class BatchScanAdmin(admin.ModelAdmin):
    list_display = ('id', 'batchtype', 'date_scanned', 'processed')
    list_filter = ('batchtype', 'processed')
    fields = ('id', 'batchtype', 'data', 'date_scanned', 'processed', 'processing_log', 'original_data')
    readonly_fields = ('id', 'original_data')
    actions = ('process_batch',)

    def process_batch(self, request, queryset):
        for bs in queryset:
            processbatchscan.process_batchscan(bs.id)
            self.message_user(request, "Processed batch %d" % bs.id)

    process_batch.short_description = "Process Batch"


admin.site.register(BatchScan, BatchScanAdmin)

# admin.site.register(Event)

# class TaskAdmin ( admin.ModelAdmin ):
#     def due_at_date ( self, task ):
#         return task.due_at.auto_occur
#     def due_occurred ( self, task ):
#         return task.due_at.occurred
#     list_display = ( 'summary', 'due_at', 'due_at_date', 'due_occurred', 'done', 'actor' )
#     list_filter = ( 'done', 'actor' )

# admin.site.register(Task,TaskAdmin)


class ChequePaymentAdmin(admin.ModelAdmin):
    def cheque_amount(self, obj):
        return -obj.amount

    # noinspection PyUnusedLocal
    def print_cheques(self, request, cheqs):
        return render(request, 'artshow/cheque.html', {'cheques': cheqs})

    list_display = ('artist', 'date', 'payee', 'number', 'cheque_amount')
    list_editable = ('number', )
    search_fields = ('artist__artistid', 'artist__name', 'payee', 'number')
    fields = ('artist', 'date', 'payee', 'number', 'amount')
    raw_id_fields = ('artist', )
    actions = ('print_cheques',)


admin.site.register(ChequePayment, ChequePaymentAdmin)
