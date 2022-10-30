from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name="login"),
    path('oauth_redirect/', views.oauth_redirect, name='oauth-redirect'),
    path('oauth_complete/', views.oauth_complete, name='oauth-complete'),
    path('logout/', auth_views.LogoutView.as_view(), name="logout"),
]
