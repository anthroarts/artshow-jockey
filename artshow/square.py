import json
import logging
import uuid

from decimal import Decimal

from django.http import HttpResponse
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from functools import cache

from square.client import Client
from square.utilities.webhooks_helper import is_valid_webhook_event_signature

from .conf import settings
from .models import SquarePayment, SquareTerminal, SquareWebhook

logger = logging.getLogger(__name__)


@cache
def client():
    return Client(
        access_token=settings.ARTSHOW_SQUARE_ACCESS_TOKEN,
        environment=settings.ARTSHOW_SQUARE_ENVIRONMENT)


def create_payment_url(artist, name, amount, redirect_url):
    result = client().checkout.create_payment_link({
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


def create_device_code(name):
    result = client().devices.create_device_code({
        'idempotency_key': str(uuid.uuid4()),
        'device_code': {
            'name': name,
            'location_id': settings.ARTSHOW_SQUARE_LOCATION_ID,
            'product_type': 'TERMINAL_API',
        },
    })

    if result.is_success():
        return result.body['device_code']['code']

    elif result.is_error():
        for error in result.errors:
            logger.error(f"Square error {error['category']}:{error['code']}: {error['detail']}")
        return None


def create_terminal_checkout(device_id, amount, reference_id, note):
    client().terminal.create_terminal_checkout({
        'idempotency_key': str(uuid.uuid4()),
        'checkout': {
            'amount_money': {
                'amount': int(amount * 100),
                'currency': 'USD',
            },
            'reference_id': reference_id,
            'device_options': {
                'device_id': device_id,
                'skip_receipt_screen': True,
                'tip_settings': {
                    'allow_tipping': False,
                },
            },
            'note': note,
        },
    })


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

    try:
        square_payment = SquarePayment.objects.get(order_id=order_id)
        square_payment.amount = payment_amount
        square_payment.payment_type_id = settings.ARTSHOW_PAYMENT_RECEIVED_PK
        square_payment.payment_id = payment_id
        square_payment.save()
    except SquarePayment.DoesNotExist:
        logger.info(f'Got webhook for unknown order: {order_id}')


def process_device_paired(body):
    device_code = body['data']['object']['device_code']

    if device_code['status'] != 'PAIRED':
        return

    device = SquareTerminal()
    device.device_id = device_code['device_id']
    device.code = device_code['code']
    device.name = device_code['name']
    device.save()


def process_webhook(body):
    if body['type'] in ('payment.created', 'payment.updated'):
        process_payment_created_or_updated(body)
    if body['type'] == 'device.code.paired':
        process_device_paired(body)


@csrf_exempt
def webhook(request):
    body = request.body.decode('utf-8')
    valid = is_valid_webhook_event_signature(
        body,
        request.headers['x-square-hmacsha256-signature'],
        settings.ARTSHOW_SQUARE_SIGNATURE_KEY,
        settings.SITE_ROOT_URL + reverse('square-webhook'))

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
