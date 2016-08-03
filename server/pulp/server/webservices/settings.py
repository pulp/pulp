
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

import django

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = 'I_am_a_secret_that_is_never_used_meaningfully_by_pulp'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False


ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = (
)

MIDDLEWARE_CLASSES = (
    'django.middleware.http.ConditionalGetMiddleware',
    'pulp.server.webservices.middleware.exception.ExceptionHandlerMiddleware',
    'pulp.server.webservices.middleware.postponed.PostponedOperationMiddleware',
    'django.middleware.common.CommonMiddleware',
)

if django.VERSION[0] == 1 and django.VERSION[2] <= 6:
    ROOT_URLCONF = 'pulp.server.webservices.compat_urls'
else:
    ROOT_URLCONF = 'pulp.server.webservices.urls'


WSGI_APPLICATION = 'pulp.server.webservices.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.4/ref/settings/#databases
# Pulp doesn't give Django a connection to the database, but it needs to be defined for 1.4 tests
# to pass.

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


# Internationalization
# https://docs.djangoproject.com/en/1.4/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.4/howto/static-files/

STATIC_URL = '/static/'

# More information on this https://docs.djangoproject.com/en/1.9/ref/templates/upgrading/
TEMPLATE_DEBUG = False
TEMPLATES = [
    {
        'OPTIONS': {'debug': False},
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
    }
]
