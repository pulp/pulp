import ConfigParser
import logging
import os

from pulp.server import logs as pulp_logs
from pulp.server import config


try:
    log_level = config.config.get('server', 'log_level')
    log_level = getattr(logging, log_level.upper())
except (ConfigParser.NoOptionError, AttributeError):
    # If the user didn't provide a log level, or if they provided an invalid one, let's use the
    # default log level
    log_level = pulp_logs.DEFAULT_LOG_LEVEL

# Rather than using `pulp.server.logs.start_logging`, which dates back to the
# pre-Django days, use Django to set up the logging. This is intended to mimic
# the functionality of `start_logging`.
LOGGING = {
    'version': 1,
    'formatters': {
        'simple': {'format': pulp_logs.LOG_FORMAT_STRING},
    },
    'handlers': {
        'syslog': {
            'address': pulp_logs.LOG_PATH,
            'facility': pulp_logs.CompliantSysLogHandler.LOG_DAEMON,
            'class': 'pulp.server.logs.CompliantSysLogHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        # Logger for the content.wsgi application.
        'pulp.server.content.web': {
            'handlers': ['syslog'],
            'level': log_level,
        },
        # Logs from unhandled exceptions in the view layer come from django
        'django': {
            'handlers': ['syslog'],
        },
    }
}


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SECRET_KEY = 'I_am_a_secret_that_is_never_used_meaningfully_by_pulp'
DEBUG = False
TEMPLATE_DEBUG = False
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

TEMPLATE_DIRS = ('/usr/share/pulp/templates/',)
