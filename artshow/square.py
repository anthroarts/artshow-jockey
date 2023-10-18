import json
import logging
import uuid

from decimal import Decimal

from django.http import HttpResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from square.client import Client
from square.utilities.webhooks_helper import is_valid_webhook_event_signature

from .conf import settings
from .models import SquarePayment, SquareWebhook

logger = logging.getLogger(__name__)


def create_payment_url(artist, name, amount, redirect_url):
    client = Client(
        access_token=settings.ARTSHOW_SQUARE_ACCESS_TOKEN,
        environment=settings.ARTSHOW_SQUARE_ENVIRONMENT)

    result = client.checkout.create_payment_link({
        'idempotency_key': str(uuid.uuid4()),
        'quick_pay': {
            'name': name,
            'price_money': {
                'amount': int(amount * 100),
                'currency': 'USD',
            },
            'location_id': settings.ARTSHOW_SQUARE_LOCATION_ID,
        },
        'checkout_options': {
            'redirect_url': redirect_url,
        },
    })

    if result.is_success():
        payment_link = result.body['payment_link']
        payment = SquarePayment(
            artist=artist,
            amount=amount,
            payment_type_id=settings.ARTSHOW_PAYMENT_PENDING_PK,
            description='Square payment',
            date=now(),
            payment_link_id=payment_link['id'],
            payment_link_url=payment_link['long_url'],
            order_id=payment_link['order_id'],
        )
        payment.save()
        return payment.payment_link_url

    elif result.is_error():
        for error in result.errors:
            logger.error(f"Square error {error['category']}:{error['code']}: {error['detail']}")
        return None


def process_payment_created_or_updated(body):
    payment = body['data']['object']['payment']

    if payment['status'] != 'COMPLETED':
        return

    currency = payment['total_money']['currency']
    if currency != 'USD':
        raise Exception(f'Unexpected currency: {currency}')

    order_id = payment['order_id']
    payment_id = payment['id']
    payment_amount = Decimal(payment['total_money']['amount'] / 100)

    square_payment = SquarePayment.objects.get(order_id=order_id)
    square_payment.amount = payment_amount
    square_payment.payment_type_id = settings.ARTSHOW_PAYMENT_RECEIVED_PK
    square_payment.payment_id = payment_id
    square_payment.save()


def process_webhook(body):
    if body['type'] in ('payment.created', 'payment.updated'):
        process_payment_created_or_updated(body)


@csrf_exempt
def webhook(request):
    body = request.body.decode('utf-8')
    valid = is_valid_webhook_event_signature(
        body,
        request.headers['x-square-hmacsha256-signature'],
        settings.ARTSHOW_SQUARE_SIGNATURE_KEY,
        settings.ARTSHOW_SQUARE_NOTIFICATION_URL)

    if not valid:
        logger.debug('Received invalid webhook!')
        return HttpResponse(status=403)

    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        logger.exception('Received webhook with invalid JSON!')
        return HttpResponse(status=400)

    webhook = SquareWebhook(timestamp=now(), body=body)
    webhook.save()

    try:
        process_webhook(body)
    except Exception:
        logger.exception('Failed to process webhook!')

    return HttpResponse(status=200)
