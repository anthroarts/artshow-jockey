from django.core import mail
from django.db.models import F
from django.template.loader import render_to_string

from artshowjockey.celery import app

from .models import Bidder, BulkMessagingTask
from .utils import artshow_settings
from . import telegram


@app.task(rate_limit='1/s')
def send_email(task_pk, recipient, subject, message):
    mail.send_mail(
        subject=subject,
        message=message,
        from_email=artshow_settings.ARTSHOW_EMAIL_SENDER,
        recipient_list=[recipient],
    )

    BulkMessagingTask.objects.filter(pk=task_pk).update(sent_count=F('sent_count') + 1)


@app.task(rate_limit='1/s')
def send_telegram_message(task_pk, chat_id, text):
    telegram.send_message(chat_id, text)

    BulkMessagingTask.objects.filter(pk=task_pk).update(sent_count=F('sent_count') + 1)


@app.task
def email_results():
    bidders = Bidder.objects.filter(person__email_confirmed=True)

    task = BulkMessagingTask(name='Send results via email')
    task.message_count = bidders.count()
    task.save()

    for bidder in bidders:
        pieces_won, pieces_not_won, pieces_in_voice_auction = \
            bidder.get_results()
        text_content = render_to_string('artshow/bid_results_email.txt', {
            'artshow_settings': artshow_settings,
            'bidder': bidder,
            'pieces_won': pieces_won,
            'pieces_not_won': pieces_not_won,
            'pieces_in_voice_auction': pieces_in_voice_auction,
        })
        send_email.delay(
            task_pk=task.pk,
            recipient=bidder.person.email,
            subject=f'{artshow_settings.SITE_NAME} Results',
            message=text_content,
        )


@app.task
def telegram_results():
    bidders = Bidder.objects.filter(person__telegram_chat_id__isnull=False)

    task = BulkMessagingTask(name='Send results via Telegram')
    task.message_count = bidders.count()
    task.save()

    for bidder in bidders:
        pieces_won, pieces_not_won, pieces_in_voice_auction = \
            bidder.get_results()
        text_content = render_to_string('artshow/bid_results_message.txt', {
            'artshow_settings': artshow_settings,
            'bidder': bidder,
            'pieces_won': pieces_won,
            'pieces_not_won': pieces_not_won,
            'pieces_in_voice_auction': pieces_in_voice_auction,
        })
        send_telegram_message.delay(
            task_pk=task.pk,
            chat_id=bidder.person.telegram_chat_id,
            text=text_content)
