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

from pulp.server.config import config
from pulp.server.constants import PULP_DJANGO_SETTINGS_MODULE

os.environ.setdefault("DJANGO_SETTINGS_MODULE", PULP_DJANGO_SETTINGS_MODULE)

broker_url = config.get('tasks', 'broker_url')
celery = Celery('tasks', broker=broker_url)


DEDICATED_QUEUE_EXCHANGE = 'C.dq'
RESOURCE_MANAGER_QUEUE = 'resource_manager'
CELERYBEAT_SCHEDULE = {
    'reap_expired_documents': {
        'task': 'pulp.server.db.reaper.queue_reap_expired_documents',
        'schedule': timedelta(days=config.getfloat('data_reaping', 'reaper_interval')),
        'args': tuple(),
    },
    'monthly_maintenance': {
        'task': 'pulp.server.maintenance.monthly.queue_monthly_maintenance',
        'schedule': timedelta(days=30),
        'args': tuple(),
    },
    'download_deferred_content': {
        'task': 'pulp.server.controllers.repository.download_deferred',
        'schedule': timedelta(minutes=config.getint('lazy', 'download_interval')),
        'args': tuple(),
    },
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
    login_method = config.get('tasks', 'login_method')
    if login_method is not '':
        celery.conf.update(BROKER_LOGIN_METHOD=login_method)


def configure_SSL():
    """
    Configures the celery object with BROKER_USE_SSL options
    """
    if config.getboolean('tasks', 'celery_require_ssl'):
        BROKER_USE_SSL = {
            'ca_certs': config.get('tasks', 'cacert'),
            'keyfile': config.get('tasks', 'keyfile'),
            'certfile': config.get('tasks', 'certfile'),
            'cert_reqs': ssl.CERT_REQUIRED,
        }
        celery.conf.update(BROKER_USE_SSL=BROKER_USE_SSL)

configure_SSL()
configure_login_method()
