from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Bidder
from .utils import artshow_settings

LOGIN_URL = reverse('artshow-bid-login')

@login_required(login_url=LOGIN_URL)
def index(request):
    try:
        bidder = Bidder.objects.get(person__user=request.user)
        return render(request, "artshow/bid_index.html", {
            'bidder': bidder,
            'artshow_settings': artshow_settings
        })
    except Bidder.DoesNotExist:
        return redirect(reverse('artshow-bid-register'))

def login(request):
    return render(request, "artshow/bid_login.html", {'artshow_settings': artshow_settings})

@login_required(login_url=LOGIN_URL)
def register(request):
    return render(request, "artshow/bid_register.html", {'artshow_settings': artshow_settings})
