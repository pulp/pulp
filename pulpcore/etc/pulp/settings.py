"""
Pulp server configuration

Values shown are the default values used, unless otherwise indicated.

Django settings for the Pulp Platform application

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

# import os
# from contextlib import suppress
# from importlib import import_module
# from pkg_resources import iter_entry_points
#
#
# # Quick-start development settings - unsuitable for production
# # See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/
#
# # SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = False
#
# ALLOWED_HOSTS = ['*']
#
# MEDIA_ROOT = '/var/lib/pulp/'
# DEFAULT_FILE_STORAGE = 'pulpcore.app.models.storage.FileSystem'
#
# FILE_UPLOAD_TEMP_DIR = '/var/lib/pulp/tmp/'
# # List of upload handler classes to be applied in order.
# FILE_UPLOAD_HANDLERS = (
#     'pulpcore.app.files.HashingFileUploadHandler',
# )
#
# # Dynaconf Configuration
#
# SECRET_KEY = True
#
# GLOBAL_ENV_FOR_DYNACONF = "PULP"
#
# ENVVAR_FOR_DYNACONF = "PULP_SETTINGS"
#
# SETTINGS_MODULE_FOR_DYNACONF = "/etc/pulp/settings.py"
#
#
# # Application definition
#
# INSTALLED_APPS = [
#     # Dynamic configuration with Dynaconf
#     'dynaconf.contrib.django_dynaconf',
#     # django stuff
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.staticfiles',
#     # third-party
#     'django_filters',
#     'drf_yasg',
#     'rest_framework',
#     # pulp core app
#     'pulpcore.app',
# ]
#
# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [os.path.join(BASE_DIR, 'templates')],
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.debug',
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#             ],
#         },
#     },
# ]
#
# # Internationalization
# # https://docs.djangoproject.com/en/1.11/topics/i18n/
#
# LANGUAGE_CODE = 'en-us'
#
# TIME_ZONE = 'UTC'
#
# USE_I18N = True
#
# USE_L10N = True
#
# USE_TZ = True
#
#
# # Static files (CSS, JavaScript, Images)
# # https://docs.djangoproject.com/en/1.11/howto/static-files/
#
# STATIC_URL = '/static/'
#
# # https://docs.djangoproject.com/en/1.11/ref/settings/#databases
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': 'pulp',
#         'USER': 'pulp',
#         'CONN_MAX_AGE': 0,
#     },
# }
# # https://docs.djangoproject.com/en/1.11/ref/settings/#logging and
# # https://docs.python.org/3/library/logging.config.html
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'simple': {'format': 'pulp: %(name)s:%(levelname)s: %(message)s'},
#     },
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#             'formatter': 'simple'
#         }
#     },
#     'loggers': {
#         '': {
#             # The root logger
#             'handlers': ["console"],
#             'level': 'INFO'
#         },
#     }
# }
#
# WORKING_DIRECTORY = '/var/lib/pulp/tmp'
#
# CONTENT_HOST = None
# CONTENT_PATH_PREFIX = '/pulp/content/'
