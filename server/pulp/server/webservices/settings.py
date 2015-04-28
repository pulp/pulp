
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'I_am_a_secret_that_is_never_used_meaningfully_by_pulp'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
)

MIDDLEWARE_CLASSES = (
    'django.middleware.http.ConditionalGetMiddleware',
    'pulp.server.webservices.middleware.exception.ExceptionHandlerMiddleware',
    'pulp.server.webservices.middleware.postponed.PostponedOperationMiddleware',
    'django.middleware.common.CommonMiddleware',
)

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
