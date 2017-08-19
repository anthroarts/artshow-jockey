from decimal import Decimal
from urllib2 import urlopen
from urlparse import parse_qs
import datetime
from django.core.signing import Signer
from django.core.urlresolvers import reverse
from django.dispatch import Signal, receiver
from django.http import HttpResponse
from django.utils.http import urlencode
import re
from .conf import settings
from logging import getLogger
from django.views.decorators.csrf import csrf_exempt
from .models import Payment
import django.utils.timezone

paypal_logger = getLogger("paypal")

pstzone = django.utils.timezone.get_fixed_timezone(-480)
pdtzone = django.utils.timezone.get_fixed_timezone(-420)

paypal_date_re = re.compile(r"(\d+:\d+:\d+ \w+ \d+, \d+) (\w+)")

def convert_date(datestr):

    # PayPal uses dates in the format: HH:MM:SS Mmm DD, YYYY PST/PDT
    # We can't use %Z to match the timezone information as this ONLY works
    # if the local computer is in a PST/PDT timezone. (see strptime(3))

    mo = paypal_date_re.match(datestr)
    if not mo:
        raise ValueError("%s is not a recognisable date" % datestr)
    datepart = mo.group(1)
    tzpart = mo.group(2)
    if tzpart == "PST":
        tzinfo = pstzone
    elif tzpart == "PDT":
        tzinfo = pdtzone
    else:
        raise ValueError("Only PST or PDT is accepted for PayPal dates. Received %s" % tzpart)

    d = datetime.datetime.strptime(datepart, "%H:%M:%S %b %d, %Y")
    d = d.replace(tzinfo=tzinfo)
    return d



# Example URL
# https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business=sales%40internetwonders.com&undefined_quantity=0&
# item_name=Art+Show+Payment&item_number=12345-123124134&amount=23&shipping=0&no_shipping=1&return=internetwonders.com&
# cancel_return=internetwonders.com&currency_code=USD&bn=PP%2dBuyNowBF&cn=&charset=UTF%2d8


def make_paypal_url(request, payment):

    signer = Signer()
    item_number = signer.sign(unicode(payment.id))

    params = {"cmd": "_xclick",
              "business": settings.ARTSHOW_PAYPAL_ACCOUNT,
              "undefined_quantity": "0",
              "item_name": "Art Show Payment from " + payment.artist.artistname(),
              "item_number": item_number,
              "amount": unicode(payment.amount),
              "shipping": "0",
              "no_shipping": "1",
              "return": request.build_absolute_uri(reverse("artshow-manage-payment-paypal",
                                                           args=(payment.artist_id,))),
              "cancel_return": request.build_absolute_uri(
                  reverse("artshow-manage-payment-paypal-cancelled",
                          args=(payment.artist_id,)) + "?" + urlencode({"item_number": item_number})),
              "currency_code": "USD",
              "bn": "PP-BuyNow",
              "charset": "UTF-8",
              "notify_url": request.build_absolute_uri(reverse(ipn_handler)),
              }

    return settings.ARTSHOW_PAYPAL_URL + "?" + urlencode(params)


ipn_received = Signal(providing_args=["query"])


class IPNProcessingError(Exception):
    pass


@receiver(ipn_received)
def process_ipn(sender, **kwargs):

    query = kwargs['query']
    payment_id = None

    try:
        verify_url = settings.ARTSHOW_PAYPAL_URL + "?cmd=_notify-validate&" + query
        paypal_logger.debug("requesting verification from: %s", verify_url)
        pipe = urlopen(verify_url)
        text = pipe.read(128)

        if text != "VERIFIED":
            raise IPNProcessingError("Paypal returned %s for verification" % text)

        params = parse_qs(query)
        paypal_logger.info("validated PayPal IPN: %s", repr(params))

        txn_type = params['txn_type'][0]
        if txn_type != "web_accept":
            raise IPNProcessingError("txn_type is %s not web_accept" % txn_type)

        item_number = params['item_number'][0]
        payment_status = params['payment_status'][0]
        amount_gross = params['mc_gross'][0]
        amount_gross = Decimal(amount_gross)
        payer_email = params['payer_email'][0]
        payment_date_str = params['payment_date'][0]

        payment_date = convert_date(payment_date_str)

        if payment_status != "Completed":
            raise IPNProcessingError("payment status is %s != Completed" % payment_status)

        signer = Signer()
        payment_id = signer.unsign(item_number)
        payment = Payment.objects.get(id=payment_id)

        if payment.payment_type_id != settings.ARTSHOW_PAYMENT_PENDING_PK:
            if payment.payment_type_id == settings.ARTSHOW_PAYMENT_RECEIVED_PK and payment.amount == amount_gross:
                paypal_logger.info("additional notification received for payment id %s. this is normal", payment_id)
                return
            raise IPNProcessingError("payment is not Payment Pending state")

        if payment.amount != amount_gross:
            paypal_logger.warning("payment is being changed from %s to %s", payment.amount, amount_gross)

        paypal_logger.info("marking payment received. payment id: %s  amount: %s  paypal email: %s",
                           payment_id, amount_gross, payer_email)

        payment.amount = amount_gross
        payment.payment_type_id = settings.ARTSHOW_PAYMENT_RECEIVED_PK
        payment.description = "Paypal " + payer_email
        payment.date = payment_date
        payment.save()

    except Exception, x:
        paypal_logger.error("Error when getting validation for: %s", query)
        if payment_id:
            paypal_logger.error("... during processing of payment_id: %s", payment_id)
        paypal_logger.error("%s", x)


@csrf_exempt
def ipn_handler(request):

    if request.method == "POST":
        query_string = request.body
    else:
        query_string = request.META['QUERY_STRING']

    paypal_logger.debug("received IPN notification with query: %s ", query_string)
    ipn_received.send(None, query=query_string)

    return HttpResponse("", content_type="text/plain")
