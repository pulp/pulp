"""
Django settings for the Pulp Platform application

Never import this module directly, instead `from django.conf import settings`, see
https://docs.djangoproject.com/en/1.11/topics/settings/#using-settings-in-python-code

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import sys
from contextlib import suppress
from importlib import import_module
from pkg_resources import iter_entry_points

import yaml

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*']

MEDIA_ROOT = '/var/lib/pulp/'
DEFAULT_FILE_STORAGE = 'pulpcore.app.models.storage.FileSystem'

FILE_UPLOAD_TEMP_DIR = '/var/lib/pulp/tmp/'
# List of upload handler classes to be applied in order.
FILE_UPLOAD_HANDLERS = (
    'pulpcore.app.files.HashingFileUploadHandler',
)


# Application definition

INSTALLED_APPS = [
    # django stuff
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # third-party
    'django_filters',
    'drf_yasg',
    'rest_framework',
    # pulp core app
    'pulpcore.app',
]

# Enumerate the installed Pulp plugins during the loading process for use in the status API
INSTALLED_PULP_PLUGINS = []

for entry_point in iter_entry_points('pulpcore.plugin'):
    plugin_app_config = entry_point.load()
    INSTALLED_PULP_PLUGINS.append(entry_point.module_name)
    INSTALLED_APPS.append(plugin_app_config)

# Optional apps that help with development, or augment Pulp in some non-critical way
OPTIONAL_APPS = [
    'crispy_forms',
    'django_extensions'
]

for app in OPTIONAL_APPS:
    # only import if app is installed
    with suppress(ImportError):
        import_module(app)
        INSTALLED_APPS.append(app)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pulpcore.app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pulpcore.app.wsgi.application'

REST_FRAMEWORK = {
    'URL_FIELD_NAME': '_href',
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_PAGINATION_CLASS': 'pulpcore.app.pagination.UUIDPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'UPLOADED_FILES_USE_URL': False,
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
}
AUTH_USER_MODEL = 'pulp_app.User'

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'

# A set of default settings to use if the configuration file in
# /etc/pulp/ is missing or if it does not have values for every setting
_DEFAULT_PULP_SETTINGS = {
    # https://docs.djangoproject.com/en/1.11/ref/settings/#databases
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'pulp',
            'USER': 'pulp',
            'CONN_MAX_AGE': 0,
        },
    },
    # https://docs.djangoproject.com/en/1.11/ref/settings/#logging and
    # https://docs.python.org/3/library/logging.config.html
    'logging': {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {'format': 'pulp: %(name)s:%(levelname)s: %(message)s'},
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'simple'
            },
            'syslog': {
                'address': '/dev/log',
                'class': 'logging.handlers.SysLogHandler',
                'formatter': 'simple'
            }
        },
        'loggers': {
            '': {
                # The root logger
                'handlers': ["syslog"],
                'level': 'INFO'
            },
        }
    },
    'SERVER': {
        'WORKING_DIRECTORY': '/var/lib/pulp/tmp',
    },
    'CONTENT': {
        'WEB_SERVER': 'django',
        'HOST': None,
    },
    'REDIS': {
        'HOST': '127.0.0.1',
        'PORT': 6379,
        'PASSWORD': ''
    },
    'PROFILING': {
        'ENABLED': False,
        'DIRECTORY': '/var/lib/pulp/c_profiles'
    }
}


def merge_settings(default, override):
    """
    Merge override settings into a set of default settings.

    If both default and override have a key that has a dictionary value, these
    dictionaries are merged recursively. If either of the values are _not_ a
    dictionary, the override key's value is used.
    """
    if not override:
        return default
    merged = default.copy()

    for key in override:
        if key in merged:
            if isinstance(default[key], dict) and isinstance(override[key], dict):
                merged[key] = merge_settings(default[key], override[key])
            else:
                merged[key] = override[key]
        else:
            merged[key] = override[key]

    return merged


def load_settings(paths=None):
    """
    Load one or more configuration files, merge them with the defaults, and apply them
    to this module as module attributes.

    Be aware that the order the paths are provided in matters. Settings are repeatedly
    overridden so settings in the last file in the list win.

    Args:
        paths: A list of absolute path strings to configuration files in YAML format.

    Returns:
        dict: The merged settings. This is helpful to see what settings Pulp is contributing, but
            is not the full set of settings Django uses, as there are a set of Django-provided
            defaults as well.
    """
    settings = _DEFAULT_PULP_SETTINGS

    for path in (paths or []):
        with suppress(OSError, IOError):
            # Consider adding logging of some kind, potentially to /var/log/pulp
            with open(path) as config_file:
                config = config_file.read()
                override_settings = yaml.safe_load(config)
                settings = merge_settings(settings, override_settings)

    for setting_name, setting_value in settings.items():
        setattr(sys.modules[__name__], setting_name.upper(), setting_value)

    return settings


# Read PULP_SETTINGS environment variable to find the location of server.yaml,
# defaults to /etc/pulp/server.yaml
PULP_SETTINGS = os.getenv('PULP_SETTINGS', '/etc/pulp/server.yaml')
load_settings([PULP_SETTINGS])
