import os


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
