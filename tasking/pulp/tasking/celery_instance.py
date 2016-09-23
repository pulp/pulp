"""
Due to our factory, we cannot put the instantiation of the Celery application into our app.py
module, as it will lead to circular dependencies since tasks.py also need to import this object, and
the factory ends up importing tasks.py when it imports all the managers.

Hopefully we will eliminate the factory in the future, but until then this workaround is necessary.
"""
from datetime import timedelta
import os
import ssl

from celery import Celery

from pulp.app import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'pulp.app.settings')

broker_url = settings.BROKER['url']
celery = Celery('tasks', broker=broker_url)


DEDICATED_QUEUE_EXCHANGE = 'C.dq'
RESOURCE_MANAGER_QUEUE = 'resource_manager'
CELERYBEAT_SCHEDULE = {
}


celery.conf.update(CELERYBEAT_SCHEDULE=CELERYBEAT_SCHEDULE)
celery.conf.update(CELERYBEAT_SCHEDULER='pulp.server.async.scheduler.Scheduler')
celery.conf.update(CELERY_WORKER_DIRECT=True)
celery.conf.update(CELERY_TASK_SERIALIZER='json')
celery.conf.update(CELERY_ACCEPT_CONTENT=['json'])


def configure_login_method():
    """
    Configures the celery object with BROKER_LOGIN_METHOD if not default.
    """
    login_method = settings.BROKER['login_method']
    if login_method is not None:
        celery.conf.update(BROKER_LOGIN_METHOD=login_method)


def configure_SSL():
    """
    Configures the celery object with BROKER_USE_SSL options
    """
    if settings.BROKER['celery_require_ssl']:
        BROKER_USE_SSL = {
            'ca_certs': settings.BROKER['cacert'],
            'keyfile': settings.BROKER['keyfile'],
            'certfile': settings.BROKER['certfile'],
            'cert_reqs': ssl.CERT_REQUIRED,
        }
        celery.conf.update(BROKER_USE_SSL=BROKER_USE_SSL)

configure_SSL()
configure_login_method()
