from django.urls import re_path

from . import bid

urlpatterns = [
    re_path(r'^$', bid.index, name='artshow-bid'),
    re_path(r'^login/$', bid.login, name='artshow-bid-login'),
    re_path(r'^register/$', bid.register, name='artshow-bid-register'),
    re_path(r'^telegram/$', bid.telegram, name='artshow-bid-telegram'),
    re_path(r'^email/send_code/$', bid.send_email_code, name='artshow-bid-send-email-code'),
    re_path(r'^email/confirm/$', bid.confirm_email, name='artshow-bid-confirm-email'),
]
