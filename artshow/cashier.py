# Artshow Jockey
# Copyright (C) 2009, 2010, 2011 Chris Cogdon
# See file COPYING for licence details
from collections import OrderedDict
from io import StringIO
import subprocess
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from .models import (
    Bidder, Piece, InvoicePayment, InvoiceItem, Invoice, SquareInvoicePayment,
    SquareTerminal
)
from django import forms
from django.db.models import Q
from django.forms import ModelForm
from .conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging
from . import invoicegen
from . import pdfreports
from . import square
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.utils import timezone
from django.utils.dateformat import DateFormat
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import (
    require_GET, require_POST, require_http_methods
)
from .conf import _DISABLED as SETTING_DISABLED

ALLOWED_PAYMENT_METHODS = OrderedDict([
    (InvoicePayment.PaymentMethod.CASH, "Cash"),
    (InvoicePayment.PaymentMethod.MANUAL_CARD, "Manual Card"),
    (InvoicePayment.PaymentMethod.SQUARE_CARD, "Square Terminal"),
])


logger = logging.getLogger(__name__)


class BidderSearchForm (forms.Form):
    text = forms.CharField(label="Search Text")


@require_http_methods(['GET', 'POST'])
@permission_required('artshow.add_invoice')
def cashier(request):
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
    return render(request, 'artshow/cashier.html', c)


class PaymentForm (ModelForm):
    class Meta:
        model = InvoicePayment
        fields = ("amount", "payment_method", "notes")
        widgets = {'amount': forms.HiddenInput, 'payment_method': forms.HiddenInput, 'notes': forms.HiddenInput}

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise ValidationError("amount must be greater than 0")
        return amount

    def clean_payment_method(self):
        payment_method = self.cleaned_data['payment_method']
        if payment_method not in ALLOWED_PAYMENT_METHODS:
            raise ValidationError("payment method is not allowed")
        return payment_method


class SelectPieceForm (forms.Form):
    select = forms.BooleanField(required=False)


# TODO probably need a @transaction.commit_on_success here

@require_http_methods(['GET', 'POST'])
@permission_required('artshow.add_invoice')
def cashier_bidder(request, bidder_id):

    bidder = get_object_or_404(Bidder, pk=bidder_id)

    all_bids = bidder.top_bids(unsold_only=True)
    available_bids = []
    pending_bids = []
    for bid in all_bids:
        if bid.piece.status == Piece.StatusWon:
            available_bids.append(bid)
        else:
            pending_bids.append(bid)

    tax_rate = settings.ARTSHOW_TAX_RATE
    error = None

    if request.method == "POST":
        for bid in available_bids:
            form = SelectPieceForm(request.POST, prefix="bid-%d" % bid.pk)
            bid.form = form

        if all(bid.form.is_valid() for bid in available_bids):

            logger.debug("Bids and Items Form passed")

            selected_bids = [bid for bid in available_bids if bid.form.cleaned_data['select']]

            if len(selected_bids) == 0:
                error = "Invoice must contain at least one item"
            else:
                subtotal = sum([bid.amount for bid in selected_bids], Decimal(0))
                tax_paid = subtotal * Decimal(tax_rate)

                invoice = Invoice(payer=bidder, tax_paid=tax_paid, paid_date=timezone.now(),
                                  created_by=request.user)
                invoice.save()

                for bid in selected_bids:
                    invoice_item = InvoiceItem(piece=bid.piece, price=bid.amount, invoice=invoice)
                    invoice_item.save()
                    bid.piece.status = Piece.StatusSold
                    bid.piece.save()

                return redirect(cashier_invoice, invoice_id=invoice.id)
    else:
        for bid in available_bids:
            form = SelectPieceForm(prefix="bid-%d" % bid.pk, initial={"select": False})
            bid.form = form

    return render(request, 'artshow/cashier_bidder.html', {
        'bidder': bidder,
        'available_bids': available_bids,
        'pending_bids': pending_bids,
        'tax_rate': tax_rate,
        'money_precision': settings.ARTSHOW_MONEY_PRECISION,
        'error': error,
    })


@require_GET
@permission_required('artshow.add_invoice')
def cashier_bidder_invoices(request, bidder_id):

    bidder = get_object_or_404(Bidder, pk=bidder_id)
    invoices = Invoice.objects.filter(payer=bidder).order_by('id')
    return render(request, 'artshow/cashier_bidder_invoices.html', {
        'bidder': bidder,
        'invoices': invoices,
        'money_precision': settings.ARTSHOW_MONEY_PRECISION
    })


@require_http_methods(['GET', 'POST'])
@permission_required('artshow.add_invoice')
def cashier_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    has_reproduction_rights = invoice.invoiceitem_set \
        .filter(piece__reproduction_rights_included=True) \
        .exists()

    if request.method == "POST":
        payment_form = PaymentForm(request.POST)
        if payment_form.is_valid():
            payment = payment_form.save(commit=False)
            if payment.payment_method == 5:
                try:
                    terminal = SquareTerminal.objects.get(pk=request.session.get('terminal'))
                    if terminal.checkout_id:
                        payment_form.add_error(None, 'Terminal already waiting for payment')
                        payment = None
                    else:
                        invoice_id = f'{settings.ARTSHOW_INVOICE_PREFIX}{invoice.id}'
                        note = f'{invoice_id} for Art Show Bidder {",".join(invoice.payer.bidder_ids())}'
                        result = square.create_terminal_checkout(
                            terminal.device_id,
                            payment.amount,
                            invoice_id,
                            note,
                        )
                        if result is None:
                            payment_form.add_error(None, 'Failed to create Square checkout')
                            payment = None
                        else:
                            payment = SquareInvoicePayment(
                                amount=payment.amount,
                                payment_method=InvoicePayment.PaymentMethod.SQUARE_CARD,
                                notes=payment.notes,
                                checkout_id=result,
                            )
                            terminal.checkout_id = result
                            terminal.save()

                except SquareTerminal.DoesNotExist:
                    payment_form.add_error(None, 'No Square terminal selected')
                    payment = None

            else:
                payment.complete = True

            if payment is not None:
                payment.invoice = invoice
                payment.save()

                return redirect(cashier_invoice, invoice_id=invoice.id)
    else:
        payment_form = PaymentForm()

    json_items = [{
        'code': item.piece.code,
        'name': item.piece.name,
        'artistName': item.piece.artistname(),
        'price': item.price,
        'location': item.piece.location,
        'reproductionRightsIncluded': item.piece.reproduction_rights_included,
    } for item in invoice.invoiceitem_set.all()]

    json_payments = [{
        'method': payment.get_payment_method_display(),
        'notes': payment.notes,
        'amount': payment.amount,
    } for payment in invoice.invoicepayment_set.all()]

    json_pending_payments = [
        payment.pk
        for payment in invoice.invoicepayment_set.filter(complete=False)
    ]

    invoice_date = invoice.paid_date.astimezone(timezone.get_current_timezone())
    formatted_date = DateFormat(invoice_date).format(settings.DATETIME_FORMAT)

    json_data = {
        'invoicePrefix': settings.ARTSHOW_INVOICE_PREFIX,
        'invoiceId': invoice.id,
        'invoiceDate': formatted_date,
        'bidderName': invoice.payer.name(),
        'bidderIds': invoice.payer.bidder_ids(),
        'hasReproductionRights': has_reproduction_rights,
        'items': json_items,
        'itemTotal': invoice.item_total(),
        'taxPaid': invoice.tax_paid,
        'totalPaid': invoice.total_paid(),
        'payments': json_payments,
        'pendingPayments': json_pending_payments,
        'moneyPrecision': settings.ARTSHOW_MONEY_PRECISION,
        'taxDescription': settings.ARTSHOW_TAX_DESCRIPTION,
    }

    return render(request, 'artshow/cashier_invoice.html', {
        'invoice': invoice,
        'payment_form': payment_form,
        'has_reproduction_rights': has_reproduction_rights,
        'has_pending_payments': len(json_pending_payments) > 0,
        'money_precision': settings.ARTSHOW_MONEY_PRECISION,
        'tax_description': settings.ARTSHOW_TAX_DESCRIPTION,
        'invoice_prefix': settings.ARTSHOW_INVOICE_PREFIX,
        'json_data': json_data,
        'payment_types': ALLOWED_PAYMENT_METHODS,
    })


@require_GET
@permission_required('artshow.add_invoice')
@xframe_options_sameorigin
def cashier_print_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    has_reproduction_rights = invoice.invoiceitem_set \
        .filter(piece__reproduction_rights_included=True) \
        .exists()

    return render(request, 'artshow/invoice.html', {
        'showstr': settings.ARTSHOW_SHOW_NAME,
        'taxdescstr': settings.ARTSHOW_TAX_DESCRIPTION,
        'invoice': invoice,
        'has_reproduction_rights': has_reproduction_rights,
        'invoice_prefix': settings.ARTSHOW_INVOICE_PREFIX,
    })


@require_GET
@permission_required('artshow.add_invoice')
def payment_status(request, payment_id):
    payment = get_object_or_404(InvoicePayment, pk=payment_id)

    if payment.complete:
        return HttpResponse('COMPLETE', content_type='text/plain')
    else:
        return HttpResponse('PENDING', content_type='text/plain')


@require_POST
@permission_required('artshow.add_invoice')
def payment_cancel(request, payment_id):
    payment = get_object_or_404(SquareInvoicePayment, pk=payment_id)

    if payment.complete:
        return HttpResponseBadRequest('Payment is complete')

    square.cancel_terminal_checkout(payment.checkout_id)
    return HttpResponse()


class PrintInvoiceForm (forms.Form):
    return_to = forms.CharField(required=False, widget=forms.HiddenInput)
    customer = forms.BooleanField(label="Customer", required=False)
    merchant = forms.BooleanField(label="Merchant", required=False)
    picklist = forms.BooleanField(label="Pick List", required=False)


# def do_print_invoices(request, invoice_id, copy_names):
#     try:
#         invoicegen.print_invoices([invoice_id], copy_names, to_printer=True)
#     except invoicegen.PrintingError, x:
#         messages.error(request, "Printing failed. Please ask administrator to consult error log")
#         logger.error("Printing failed with exception: %s", x)
#     else:
#         messages.info(request, "Invoice %s has been sent to the printer" % invoice_id)


def do_print_invoices2(invoice, copy_names):

    for copy_name in copy_names:
        do_print_invoices3(invoice, copy_name)


def do_print_invoices3(invoice, copy_name):

    sbuf = StringIO()

    try:
        if copy_name == "PICK LIST":
            pdfreports.picklist_to_pdf(invoice, sbuf)
        else:
            pdfreports.invoice_to_pdf(invoice, sbuf)
    except Exception as x:
        logger.error("Could not generate invoice: %s", x)
        raise invoicegen.PrintingError("Could not generate invoice: %s" % x)

    if not sbuf.getvalue():
        logger.error("nothing to generate")
    else:
        if settings.ARTSHOW_PRINT_COMMAND is SETTING_DISABLED:
            logger.error("Cannot print invoice. ARTSHOW_PRINT_COMMAND is DISABLED")
            raise invoicegen.PrintingError("Printing is DISABLED in configuration")
        p = subprocess.Popen(settings.ARTSHOW_PRINT_COMMAND, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE, shell=True)
        output, error = p.communicate(sbuf.getvalue())
        if output:
            logger.debug("printing command returned: %s", output)
        if error:
            logger.error("printing command returned error: %s", error)
            raise invoicegen.PrintingError(error)


def do_print_invoices(request, invoice_id, copy_names):
    invoice = Invoice.objects.get(id=invoice_id)
    try:
        do_print_invoices2(invoice, copy_names)
    except invoicegen.PrintingError as x:
        messages.error(request, "Printing failed. Please ask administrator to consult error log")
        logger.error("Printing failed with exception: %s", x)
    else:
        messages.info(request, "Invoice %s has been sent to the printer" % invoice_id)


@permission_required('artshow.add_invoice')
def print_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    if request.method == "POST":
        form = PrintInvoiceForm(request.POST)
        if form.is_valid():
            copy_names = []
            if form.cleaned_data['customer']:
                copy_names.append("CUSTOMER COPY")
            if form.cleaned_data['merchant']:
                copy_names.append("MERCHANT COPY")
            if form.cleaned_data['picklist']:
                copy_names.append("PICK LIST")
            do_print_invoices(request, invoice.id, copy_names)
            return_to = form.cleaned_data['return_to']
            if not return_to:
                return_to = "artshow.views.index"
            return redirect(return_to)

    messages.error(request, "Print Invoice request is invalid")
    return HttpResponseBadRequest("Print Invoice request is invalid.")
