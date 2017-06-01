import ConfigParser
import logging
import os

from pulp.server import logs as pulp_logs
from pulp.server import config


log_level = pulp_logs.get_log_level()
log_type = pulp_logs.get_log_type()

# Set up our handler and add it to the root logger
if log_type == 'syslog':
    handler = {
        'syslog': {
            'address': pulp_logs.LOG_PATH,
            'facility': pulp_logs.CompliantSysLogHandler.LOG_DAEMON,
            'class': 'pulp.server.logs.CompliantSysLogHandler',
            'formatter': 'simple',
        },
    }
elif log_type == 'console':
    handler = {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    }

# Rather than using `pulp.server.logs.start_logging`, which dates back to the
# pre-Django days, use Django to set up the logging. This is intended to mimic
# the functionality of `start_logging`.
LOGGING = {
    'version': 1,
    'formatters': {
        'simple': {'format': pulp_logs.LOG_FORMAT_STRING},
    },
    'handlers': handler,
    'loggers': {
        # Logger for the content.wsgi application.
        'pulp.server.content.web': {
            'handlers': [log_type],
            'level': log_level,
        },
        # Logs from unhandled exceptions in the view layer come from django
        'django': {
            'handlers': [log_type],
        },
        # 404 responses trigger logs at WARNING level, which is inappropriate
        # for Pulp.
        'django.request': {
            'handlers': [log_type],
            'level': 'ERROR',
        },
    }
}


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SECRET_KEY = 'I_am_a_secret_that_is_never_used_meaningfully_by_pulp'
DEBUG = False
ALLOWED_HOSTS = ['*']
INSTALLED_APPS = ()

MIDDLEWARE_CLASSES = (
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.common.CommonMiddleware'
)

ROOT_URLCONF = 'pulp.server.content.web.urls'
WSGI_APPLICATION = 'pulp.server.content.web.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': '',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'

# More information on this https://docs.djangoproject.com/en/1.9/ref/templates/upgrading/
TEMPLATE_DIRS = ['/usr/share/pulp/templates/']
TEMPLATE_DEBUG = False
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATE_DIRS,
        'OPTIONS': {'debug': False},
    }
]
