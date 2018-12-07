"""
WSGI config for pulp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulpcore.app.settings")

# https://github.com/rochacbruno/dynaconf/issues/89
from dynaconf.contrib import django_dynaconf  # noqa
from django.core.wsgi import get_wsgi_application # noqa

application = get_wsgi_application()
