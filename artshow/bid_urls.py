from django.urls import re_path

from . import bid

urlpatterns = [
    re_path(r'^$', bid.index, name='artshow-bid'),
    re_path(r'^login/$', bid.login, name='artshow-bid-login'),
    re_path(r'^register/$', bid.register, name='artshow-bid-register'),
    re_path(r'^telegram/$', bid.telegram, name='artshow-bid-telegram'),
]
