"""
WSGI config for pulp_django project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os

from pulp.server.constants import PULP_DJANGO_SETTINGS_MODULE

os.environ.setdefault("DJANGO_SETTINGS_MODULE", PULP_DJANGO_SETTINGS_MODULE)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
