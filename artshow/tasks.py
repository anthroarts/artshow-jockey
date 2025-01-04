from django.core import mail
from django.db.models import F
from django.template.loader import render_to_string

from artshowjockey.celery import app

from .models import Bidder, BulkMessagingTask
from .utils import artshow_settings
from . import telegram


@app.task(rate_limit='1/s', autoretry_for=(Exception,), retry_backoff=True)
def send_email(task_pk, recipient, subject, message):
    mail.send_mail(
        subject=subject,
        message=message,
        from_email=artshow_settings.ARTSHOW_EMAIL_SENDER,
        recipient_list=[recipient],
    )

    BulkMessagingTask.objects.filter(pk=task_pk).update(sent_count=F('sent_count') + 1)


@app.task(rate_limit='1/s', autoretry_for=(Exception,), retry_backoff=True)
def send_telegram_message(task_pk, chat_id, text):
    telegram.send_message(chat_id, text)

    BulkMessagingTask.objects.filter(pk=task_pk).update(sent_count=F('sent_count') + 1)


@app.task
def email_results():
    bidders = Bidder.objects.filter(person__email_confirmed=True)

    messages_to_send = []
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
        messages_to_send.append((bidder.person.email, text_content))

    task = BulkMessagingTask(name='Send results via email')
    task.message_count = len(messages_to_send)
    task.save()

    for (email, text_content) in messages_to_send:
        send_email.delay(
            task_pk=task.pk,
            recipient=email,
            subject=f'{artshow_settings.SITE_NAME} results',
            message=text_content,
        )


@app.task
def telegram_results():
    bidders = Bidder.objects.filter(person__telegram_chat_id__isnull=False)

    messages_to_send = []
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
        messages_to_send.append((bidder.person.telegram_chat_id, text_content))

    task = BulkMessagingTask(name='Send results via Telegram')
    task.message_count = len(messages_to_send)
    task.save()

    for (chat_id, text_content) in messages_to_send:
        send_telegram_message.delay(
            task_pk=task.pk,
            chat_id=chat_id,
            text=text_content)


@app.task
def email_voice_results(adult):
    bidders = Bidder.objects.filter(person__email_confirmed=True)
    type = 'adult' if adult else 'general'

    messages_to_send = []
    for bidder in bidders:
        pieces_won = bidder.voice_auction_wins(adult=adult)
        if pieces_won.count() > 0:
            text_content = render_to_string('artshow/voice_auction_results_email.txt', {
                'artshow_settings': artshow_settings,
                'bidder': bidder,
                'type': type,
                'pieces_won': pieces_won,
            })
            messages_to_send.append((bidder.person.email, text_content))

    task = BulkMessagingTask(name=f'Send {type} voice auction results via email')
    task.message_count = len(messages_to_send)
    task.save()

    for (email, text_content) in messages_to_send:
        send_email.delay(
            task_pk=task.pk,
            recipient=email,
            subject=f'{artshow_settings.SITE_NAME} {type} voice auction results',
            message=text_content,
        )


@app.task
def telegram_voice_results(adult):
    bidders = Bidder.objects.filter(person__telegram_chat_id__isnull=False)
    type = 'adult' if adult else 'general'

    messages_to_send = []
    for bidder in bidders:
        piece_won_count = bidder.voice_auction_wins(adult=adult).count()
        if piece_won_count > 0:
            text_content = render_to_string('artshow/voice_auction_results_message.txt', {
                'artshow_settings': artshow_settings,
                'bidder': bidder,
                'type': type,
                'piece_won_count': piece_won_count,
            })
            messages_to_send.append((bidder.person.telegram_chat_id, text_content))

    task = BulkMessagingTask(name=f'Send {type} voice auction results via Telegram')
    task.message_count = len(messages_to_send)
    task.save()

    for (chat_id, text_content) in messages_to_send:
        send_telegram_message.delay(
            task_pk=task.pk,
            chat_id=chat_id,
            text=text_content,
        )


@app.task
def email_reminder():
    bidders = Bidder.objects.filter(person__email_confirmed=True)

    messages_to_send = []
    for bidder in bidders:
        unsold_pieces = bidder.unsold_pieces()
        if unsold_pieces.count() > 0:
            text_content = render_to_string('artshow/unsold_pieces_email.txt', {
                'artshow_settings': artshow_settings,
                'bidder': bidder,
                'unsold_pieces': unsold_pieces,
            })
            messages_to_send.append((bidder.person.email, text_content))

    task = BulkMessagingTask(name='Send reminder for unsold pieces via email')
    task.message_count = len(messages_to_send)
    task.save()

    for (email, text_content) in messages_to_send:
        send_email.delay(
            task_pk=task.pk,
            recipient=email,
            subject=f'Reminder: {artshow_settings.SITE_NAME} pick-up available',
            message=text_content,
        )


@app.task
def telegram_reminder():
    bidders = Bidder.objects.filter(person__email_confirmed=True)

    messages_to_send = []
    for bidder in bidders:
        unsold_piece_count = bidder.unsold_pieces().count()
        if unsold_piece_count > 0:
            text_content = render_to_string('artshow/unsold_pieces_message.txt', {
                'artshow_settings': artshow_settings,
                'bidder': bidder,
                'unsold_piece_count': unsold_piece_count,
            })
            messages_to_send.append((bidder.person.telegram_chat_id, text_content))

    task = BulkMessagingTask(name='Send reminder for unsold pieces via Telegram')
    task.message_count = len(messages_to_send)
    task.save()

    for (chat_id, text_content) in messages_to_send:
        send_telegram_message.delay(
            task_pk=task.pk,
            chat_id=chat_id,
            text=text_content,
        )
