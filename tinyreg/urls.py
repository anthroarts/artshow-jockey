from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import CaptchaPasswordResetForm

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name="login"),
    path('logout/', auth_views.LogoutView.as_view(), name="logout"),
    path('password_change/', auth_views.PasswordChangeView.as_view(),
         name="password_change"),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(),
         name="password_change_done"),
    path('password_reset/', auth_views.PasswordResetView.as_view(),
         {
             'from_email': settings.ARTSHOW_EMAIL_SENDER,
             'password_reset_form': CaptchaPasswordResetForm,
         },
         name="password_reset"),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(),
         name="password_reset_done"),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(),
         name="password_reset_confirm"),
    path('password_reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(),
         name="password_reset_complete"),
]
