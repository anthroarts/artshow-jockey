from django.core import mail
from django.db.models import F, OuterRef, Subquery
from django.template.loader import render_to_string

from artshowjockey.celery import app

from .models import Bid, Bidder, BulkMessagingTask, Piece
from .utils import artshow_settings
from . import telegram


@app.task(rate_limit='1/s', autoretry_for=(Exception,), retry_backoff=True)
def send_results_email(task_pk, bidder_pk):
    bidder = Bidder.objects.get(pk=bidder_pk)

    pieces_won, pieces_not_won, pieces_in_voice_auction = bidder.get_results()
    text_content = render_to_string('artshow/bid_results_email.txt', {
        'artshow_settings': artshow_settings,
        'bidder': bidder,
        'pieces_won': pieces_won,
        'pieces_not_won': pieces_not_won,
        'pieces_in_voice_auction': pieces_in_voice_auction,
    })

    mail.send_mail(
        subject=f'{artshow_settings.SITE_NAME} results',
        message=text_content,
        from_email=artshow_settings.ARTSHOW_EMAIL_SENDER,
        recipient_list=[bidder.person.email],
    )

    BulkMessagingTask.objects.filter(pk=task_pk).update(sent_count=F('sent_count') + 1)


@app.task
def email_results():
    bidders = Bidder.objects.filter(person__email_confirmed=True).values_list('pk', flat=True)

    task = BulkMessagingTask(name='Send results via email')
    task.message_count = len(bidders)
    task.save()

    for bidder in bidders:
        send_results_email.delay(task_pk=task.pk, bidder_pk=bidder)


@app.task(rate_limit='1/s', autoretry_for=(Exception,), retry_backoff=True)
def send_results_telegram_message(task_pk, bidder_pk):
    bidder = Bidder.objects.get(pk=bidder_pk)

    pieces_won, pieces_not_won, pieces_in_voice_auction = bidder.get_results()
    text_content = render_to_string('artshow/bid_results_message.txt', {
        'artshow_settings': artshow_settings,
        'bidder': bidder,
        'pieces_won': pieces_won,
        'pieces_not_won': pieces_not_won,
        'pieces_in_voice_auction': pieces_in_voice_auction,
    })

    telegram.send_message(bidder.person.telegram_chat_id, text_content)

    BulkMessagingTask.objects.filter(pk=task_pk).update(sent_count=F('sent_count') + 1)


@app.task
def telegram_results():
    bidders = Bidder.objects.filter(person__telegram_chat_id__isnull=False).values_list('pk', flat=True)

    task = BulkMessagingTask(name='Send results via Telegram')
    task.message_count = len(bidders)
    task.save()

    for bidder in bidders:
        send_results_telegram_message.delay(task_pk=task.pk, bidder_pk=bidder)


@app.task(rate_limit='1/s', autoretry_for=(Exception,), retry_backoff=True)
def send_voice_results_email(task_pk, bidder_pk, adult):
    bidder = Bidder.objects.get(pk=bidder_pk)
    type = 'adult' if adult else 'general'

    text_content = render_to_string('artshow/voice_auction_results_email.txt', {
        'artshow_settings': artshow_settings,
        'bidder': bidder,
        'type': type,
        'pieces_won': bidder.voice_auction_wins(adult=adult),
    })

    mail.send_mail(
        subject=f'{artshow_settings.SITE_NAME} {type} voice auction results',
        message=text_content,
        from_email=artshow_settings.ARTSHOW_EMAIL_SENDER,
        recipient_list=[bidder.person.email],
    )

    BulkMessagingTask.objects.filter(pk=task_pk).update(sent_count=F('sent_count') + 1)


@app.task
def email_voice_results(adult):
    winning_bid_query = Bid.objects.filter(
        piece=OuterRef('pk'), invalid=False).order_by('-amount')[:1]
    winning_bidder_ids = Piece.objects.filter(
        status=Piece.StatusWon,
        voice_auction=True,
        adult=adult
    ).annotate(
        top_bidder=Subquery(winning_bid_query.values('bidder'))
    ).values_list('top_bidder', flat=True)
    bidders = Bidder.objects.filter(
        pk__in=winning_bidder_ids,
        person__email_confirmed=True).values_list('pk', flat=True)

    type = 'adult' if adult else 'general'

    task = BulkMessagingTask(name=f'Send {type} voice auction results via email')
    task.message_count = len(bidders)
    task.save()

    for bidder in bidders:
        send_voice_results_email.delay(task_pk=task.pk, bidder_pk=bidder, adult=adult)


@app.task(rate_limit='1/s', autoretry_for=(Exception,), retry_backoff=True)
def send_voice_results_telegram_message(task_pk, bidder_pk, adult):
    bidder = Bidder.objects.get(pk=bidder_pk)
    type = 'adult' if adult else 'general'

    text_content = render_to_string('artshow/voice_auction_results_message.txt', {
        'artshow_settings': artshow_settings,
        'bidder': bidder,
        'type': type,
        'piece_won_count': bidder.voice_auction_wins(adult=adult).count(),
    })

    telegram.send_message(bidder.person.telegram_chat_id, text_content)

    BulkMessagingTask.objects.filter(pk=task_pk).update(sent_count=F('sent_count') + 1)


@app.task
def telegram_voice_results(adult):
    winning_bid_query = Bid.objects.filter(
        piece=OuterRef('pk'), invalid=False).order_by('-amount')[:1]
    winning_bidder_ids = Piece.objects.filter(
        status=Piece.StatusWon,
        voice_auction=True,
        adult=adult
    ).annotate(
        top_bidder=Subquery(winning_bid_query.values('bidder'))
    ).values_list('top_bidder', flat=True)
    bidders = Bidder.objects.filter(
        pk__in=winning_bidder_ids,
        person__telegram_chat_id__isnull=False).values_list('pk', flat=True)

    type = 'adult' if adult else 'general'

    task = BulkMessagingTask(name=f'Send {type} voice auction results via Telegram')
    task.message_count = len(bidders)
    task.save()

    for bidder in bidders:
        send_voice_results_telegram_message.delay(task_pk=task.pk, bidder_pk=bidder, adult=adult)


@app.task(rate_limit='1/s', autoretry_for=(Exception,), retry_backoff=True)
def send_reminder_email(task_pk, bidder_pk):
    bidder = Bidder.objects.get(pk=bidder_pk)

    text_content = render_to_string('artshow/unsold_pieces_email.txt', {
        'artshow_settings': artshow_settings,
        'bidder': bidder,
        'unsold_pieces': bidder.unsold_pieces(),
    })

    mail.send_mail(
        subject=f'Reminder: {artshow_settings.SITE_NAME} pick-up available',
        message=text_content,
        from_email=artshow_settings.ARTSHOW_EMAIL_SENDER,
        recipient_list=[bidder.person.email],
    )

    BulkMessagingTask.objects.filter(pk=task_pk).update(sent_count=F('sent_count') + 1)


@app.task
def email_reminder():
    winning_bid_query = Bid.objects.filter(
        piece=OuterRef('pk'), invalid=False).order_by('-amount')[:1]
    winning_bidder_ids = Piece.objects.filter(status=Piece.StatusWon).annotate(
        top_bidder=Subquery(winning_bid_query.values('bidder'))
    ).values_list('top_bidder', flat=True)
    bidders = Bidder.objects.filter(
        pk__in=winning_bidder_ids,
        person__email_confirmed=True).values_list('pk', flat=True)

    task = BulkMessagingTask(name='Send reminder for unsold pieces via email')
    task.message_count = len(bidders)
    task.save()

    for bidder in bidders:
        send_reminder_email.delay(task.pk, bidder)


@app.task(rate_limit='1/s', autoretry_for=(Exception,), retry_backoff=True)
def send_reminder_telegram_message(task_pk, bidder_pk):
    bidder = Bidder.objects.get(pk=bidder_pk)

    text_content = render_to_string('artshow/unsold_pieces_message.txt', {
        'artshow_settings': artshow_settings,
        'bidder': bidder,
        'unsold_piece_count': bidder.unsold_pieces().count(),
    })

    telegram.send_message(bidder.person.telegram_chat_id, text_content)

    BulkMessagingTask.objects.filter(pk=task_pk).update(sent_count=F('sent_count') + 1)


@app.task
def telegram_reminder():
    winning_bid_query = Bid.objects.filter(
        piece=OuterRef('pk'), invalid=False).order_by('-amount')[:1]
    winning_bidder_ids = Piece.objects.filter(status=Piece.StatusWon).annotate(
        top_bidder=Subquery(winning_bid_query.values('bidder'))
    ).values_list('top_bidder', flat=True)
    bidders = Bidder.objects.filter(
        pk__in=winning_bidder_ids,
        person__telegram_chat_id__isnull=False).values_list('pk', flat=True)

    task = BulkMessagingTask(name='Send reminder for unsold pieces via Telegram')
    task.message_count = len(bidders)
    task.save()

    for bidder in bidders:
        send_reminder_telegram_message.delay(task_pk=task.pk, bidder_pk=bidder)
