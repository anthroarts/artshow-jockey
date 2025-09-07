import json
import logging
import uuid

from decimal import Decimal

from django.http import HttpResponse
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from functools import cache

from square import Square
from square.core.api_error import ApiError
from square.environment import SquareEnvironment
from square.utils.webhooks_helper import verify_signature

from .conf import settings
from .models import (
    SquareInvoicePayment, SquarePayment, SquareTerminal, SquareWebhook
)

logger = logging.getLogger(__name__)


@cache
def client():
    environment = SquareEnvironment.PRODUCTION
    if settings.ARTSHOW_SQUARE_ENVIRONMENT == 'sandbox':
        environment = SquareEnvironment.SANDBOX

    return Square(
        token=settings.ARTSHOW_SQUARE_ACCESS_TOKEN,
        environment=environment)


def log_errors(errors):
    for error in errors:
        logger.error(f"Square error {error['category']}:{error['code']}: {error['detail']}")


def create_payment_url(artist, name, amount, redirect_url):
    try:
        result = client().checkout.payment_links.create(
            idempotency_key=str(uuid.uuid4()),
            quick_pay={
                'name': name,
                'price_money': {
                    'amount': int(amount * 100),
                    'currency': 'USD',
                },
                'location_id': settings.ARTSHOW_SQUARE_LOCATION_ID,
            },
            checkout_options={
                'redirect_url': redirect_url,
            },
        )

        payment_link = result.payment_link
        payment = SquarePayment(
            artist=artist,
            amount=amount,
            payment_type_id=settings.ARTSHOW_PAYMENT_PENDING_PK,
            description='Square payment',
            date=now(),
            payment_link_id=payment_link.id,
            payment_link_url=payment_link.long_url,
            order_id=payment_link.order_id,
        )
        payment.save()
        return payment.payment_link_url
    except ApiError as e:
        log_errors(e.errors)
        return None


def create_device_code(name):
    try:
        result = client().devices.codes.create(
            idempotency_key=str(uuid.uuid4()),
            device_code={
                'name': name,
                'location_id': settings.ARTSHOW_SQUARE_LOCATION_ID,
                'product_type': 'TERMINAL_API',
            },
        )

        return result.device_code.code
    except ApiError as e:
        log_errors(e.errors)
        return None


def create_terminal_checkout(device_id, amount, reference_id, note):
    try:
        result = client().terminal.checkouts.create(
            idempotency_key=str(uuid.uuid4()),
            checkout={
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
                'payment_options': {
                    'accept_partial_authorization': False,
                },
                'note': note,
            },
        )

        return result.checkout.id
    except ApiError as e:
        log_errors(e.errors)
        return None


def cancel_terminal_checkout(checkout_id):
    try:
        client().terminal.checkouts.cancel(checkout_id)
    except ApiError as e:
        log_errors(e.errors)


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


def process_checkout_created_or_updated(body):
    checkout = body['data']['object']['checkout']

    checkout_id = checkout['id']
    checkout_status = checkout['status']
    if checkout_status in ('CANCELED', 'COMPLETED'):
        try:
            device_id = checkout['device_options']['device_id']
            terminal = SquareTerminal.objects.get(device_id=device_id)
            if checkout_id == terminal.checkout_id:
                terminal.checkout_id = ''
                terminal.save()
        except SquareTerminal.DoesNotExist:
            logger.info(f'Got webhook for unknown device: {device_id}')
            # Let processing continue, since we might have a payment to update.

    try:
        payment = SquareInvoicePayment.objects.get(checkout_id=checkout_id)
    except SquareInvoicePayment.DoesNotExist:
        logger.info(f'Got webhook for unknown checkout: {checkout_id}')
        return

    currency = checkout['amount_money']['currency']
    if currency != 'USD':
        raise Exception(f'Unexpected currency: {currency}')

    if checkout_status == 'CANCELED':
        payment.delete()
    elif checkout_status == 'COMPLETED':
        payment.amount = Decimal(checkout['amount_money']['amount'] / 100)
        payment.payment_ids = ', '.join(checkout['payment_ids'])
        payment.complete = True
        payment.save()


def process_webhook(body):
    if body['type'] in ('payment.created', 'payment.updated'):
        process_payment_created_or_updated(body)
    if body['type'] == 'device.code.paired':
        process_device_paired(body)
    if body['type'] in ('terminal.checkout.created', 'terminal.checkout.updated'):
        process_checkout_created_or_updated(body)


@csrf_exempt
def webhook(request):
    body = request.body.decode('utf-8')
    valid = verify_signature(
        request_body=body,
        signature_header=request.headers['x-square-hmacsha256-signature'],
        signature_key=settings.ARTSHOW_SQUARE_SIGNATURE_KEY,
        notification_url=settings.SITE_ROOT_URL + reverse('square-webhook'))

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
