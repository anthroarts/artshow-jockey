# Django settings for artshowjockey project.
from environs import Env, EnvError
import os

env = Env()
env.read_env()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DEBUG = env.bool('DEBUG', default=False)
SECRET_KEY = env.str('SECRET_KEY')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {"default": env.dj_db_url("DATABASE_URL")}

try:
    email = env.dj_email_url("EMAIL_URL")
    EMAIL_HOST = email["EMAIL_HOST"]
    EMAIL_PORT = email["EMAIL_PORT"]
    EMAIL_HOST_PASSWORD = email["EMAIL_HOST_PASSWORD"]
    EMAIL_HOST_USER = email["EMAIL_HOST_USER"]
    EMAIL_USE_TLS = email["EMAIL_USE_TLS"]
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
except EnvError:
    try:
        with env.prefixed('AWS_SES_'):
            AWS_SES_ACCESS_KEY_ID = env('ACCESS_KEY_ID')
            AWS_SES_SECRET_ACCESS_KEY = env('SECRET_ACCESS_KEY')
            AWS_SES_REGION_NAME = env('REGION_NAME')
            AWS_SES_REGION_ENDPOINT = env('REGION_ENDPOINT')
            AWS_SES_CONFIGURATION_SET = env('CONFIGURATION_SET')
        EMAIL_BACKEND = 'django_ses.SESBackend'
    except EnvError:
        if DEBUG:
            EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
        else:
            EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

SERVER_EMAIL = 'artshow-jockey@furtherconfusion.org'
DEFAULT_FROM_EMAIL = SERVER_EMAIL

CELERY_BROKER_URL = env.str('BROKER_URL', default='amqp://')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'queue_name_prefix':
        env.str('CELERY_QUEUE_PREFIX', default='artshowjockey-'),
}

# Configure mail sent with the backend above to go through the Celery task
# queue.
CELERY_EMAIL_BACKEND = EMAIL_BACKEND
EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'US/Pacific'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = 'static'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    # os.path.join(BASE_DIR, 'artshowjockey/static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # Put strings here, like "/home/html/django_templates" or
            # "C:/www/django/templates".
            # Always use forward slashes, even on Windows.
            # Don't forget to use absolute paths, not relative paths.
            os.path.join(BASE_DIR, 'artshowjockey/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                "tinyreg.context_processors.site_name",
                "artshow.context_processors.artshow_settings",
            ],
        },
    },
]

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'artshowjockey.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'artshowjockey.wsgi.application'

INSTALLED_APPS = (
    'tinyreg',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django_ses',
    'nocaptcha_recaptcha',
    'peeps',
    'artshow',
    'ajax_select',
    'tinyannounce',
    'django_celery_results',
    'djcelery_email',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
    },
    'loggers': {
        'artshow.square': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'paypal': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

TEST_RUNNER = 'django.test.runner.DiscoverRunner'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

AJAX_LOOKUP_CHANNELS = {
    'person': ('peeps.lookups', 'PersonLookup'),
}
# magically include jqueryUI/js/css
AJAX_SELECT_BOOTSTRAP = True
AJAX_SELECT_INLINES = 'inline'

LOGIN_REDIRECT_URL = "/"

with env.prefixed('ARTSHOW_'):
    ARTSHOW_SHOW_NAME = env.str('SHOW_NAME', default='Art Show')
    ARTSHOW_TAX_RATE = env.str('TAX_RATE', default='0.1')
    ARTSHOW_TAX_DESCRIPTION = \
        env.str('TAX_DESCRIPTION', default='Sales Tax 10%')
    ARTSHOW_EMAIL_SENDER = \
        env.str('EMAIL_SENDER', default='Art Show <artshow@example.com>')
    ARTSHOW_COMMISSION = env.str('COMMISSION', default='0.1')
    ARTSHOW_INVOICE_PREFIX = env.str('INVOICE_PREFIX', default='INV-')
    ARTSHOW_EMAIL_FOOTER = env.str('EMAIL_FOOTER', default="")
    ARTSHOW_ARTIST_AGREEMENT_URL = env.str('ARTIST_AGREEMENT_URL')

ARTSHOW_CHEQUE_THANK_YOU = \
    "Thank you for exhibiting at the " + ARTSHOW_SHOW_NAME
ARTSHOW_CHEQUES_AS_PDF = True
ARTSHOW_PRINT_COMMAND = "enscript -P Samsung -B -L 66 -f Courier-Bold10 -q"
ARTSHOW_AUTOPRINT_INVOICE = ["CUSTOMER COPY", "MERCHANT COPY", "PICK LIST"]
ARTSHOW_BLANK_BID_SHEET = "artshow/files/blank_bid_sheet.pdf"
ARTSHOW_SCANNER_DEVICE = "/dev/ttyUSB0"
ARTSHOW_SHOW_ALLOCATED_SPACES = True
ARTSHOW_MAX_PIECE_ID = 99

PEEPS_DEFAULT_COUNTRY = "USA"

with env.prefixed('NORECAPTCHA_'):
    # Visit https://www.google.com/recaptcha/admin/create to create a keypair.
    # These are test keys.
    NORECAPTCHA_SITE_KEY = env.str('SITE_KEY')
    NORECAPTCHA_SECRET_KEY = env.str('SECRET_KEY')

with env.prefixed('ARTSHOW_PAYPAL_'):
    ARTSHOW_PAYPAL_ACCOUNT = env.str('ACCOUNT')
    ARTSHOW_PAYPAL_URL = env.str('URL', 'https://www.paypal.com/cgi-bin/webscr')

with env.prefixed('ARTSHOW_SQUARE_'):
    ARTSHOW_SQUARE_APPLICATION_ID = env.str('APPLICATION_ID')
    ARTSHOW_SQUARE_LOCATION_ID = env.str('LOCATION_ID')
    ARTSHOW_SQUARE_ACCESS_TOKEN = env.str('ACCESS_TOKEN')

SITE_ID = 1
SITE_NAME = ARTSHOW_SHOW_NAME
SITE_ROOT_URL = 'https://artshow.furcon.org'
