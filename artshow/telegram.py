from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from functools import cache

import json
import logging
import requests

from .conf import settings
from .models import TelegramWebhook

logger = logging.getLogger(__name__)


@cache
def api_url():
    return f'https://api.telegram.org/bot{settings.ARTSHOW_TELEGRAM_BOT_TOKEN}'


@permission_required('artshow.is_artshow_staff')
@require_http_methods(["GET", "POST"])
def set_webhook(request):
    if request.method == 'GET':
        response = requests.get(f'{api_url()}/getWebhookInfo')
        try:
            webhook_info = response.json()
        except requests.exceptions.JSONDecodeError:
            webhook_info = "Invalid response JSON."
        return render(request, 'artshow/workflows_telegram_webhook.html',
                      {'webhook_info': webhook_info})
    elif request.method == 'POST':
        response = requests.get(f'{api_url()}/setWebhook', {
            'url': f'{settings.SITE_ROOT_URL}{reverse('telegram-webhook')}',
            'secret_token': settings.ARTSHOW_TELEGRAM_WEBHOOK_SECRET
        })
        if response.status_code == 200:
            messages.success(request, 'Webhook configured successfully')
        else:
            messages.error(request, f'Failed to configure webhook: {response.text}')
        return redirect('telegram-configure-webhook')


@permission_required('artshow.is_artshow_staff')
@require_POST
def delete_webhook(request):
    response = requests.get(f'{api_url()}/deleteWebhook')
    if response.status_code == 200:
        messages.success(request, 'Webhook deleted successfully')
    else:
        messages.error(request, f'Failed to delete webhook: {response.text}')
    return redirect('telegram-configure-webhook')


def send_message(chat_id, text):
    response = requests.post(f'{api_url()}/sendMessage', {
        'chat_id': chat_id,
        'parse_mode': 'HTML',
        'text': text
    })
    if response.status_code != 200:
        raise Exception(f'Failed to send Telegram message ({response.status_code}): {response.text}')


def process_message(message):
    if 'text' in message:
        chat_id = message['chat']['id']
        send_message(chat_id, f'Messages to this bot are not monitored. Please e-mail <a href="mailto:{settings.ARTSHOW_ADMIN_EMAIL}">{settings.ARTSHOW_ADMIN_EMAIL}</a>.')


def process_update(body):
    if 'message' in body:
        process_message(body['message'])


@csrf_exempt
@require_POST
def webhook(request):
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != settings.ARTSHOW_TELEGRAM_WEBHOOK_SECRET:
        logger.debug('Received webhook with invalid secret!')
        return HttpResponse(status=403)

    body = request.body.decode('utf-8')
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        logger.exception('Received webhook with invalid JSON!')
        return HttpResponse(status=400)

    webhook = TelegramWebhook(timestamp=now(), body=body)
    webhook.save()

    try:
        process_update(body)
    except Exception:
        logger.exception('Failed to process webhook!')

    return HttpResponse(status=200)
