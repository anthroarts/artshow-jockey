from django.contrib.auth.forms import PasswordResetForm
from nocaptcha_recaptcha.fields import NoReCaptchaField


class CaptchaPasswordResetForm(PasswordResetForm):
    captcha = NoReCaptchaField()
