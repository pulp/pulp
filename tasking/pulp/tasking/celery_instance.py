import os
import ssl

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'pulp.app.settings')

from django.conf import settings  # NOQA

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
            'ca_certs': settings.BROKER['ssl_ca_certificate'],
            'keyfile': settings.BROKER['ssl_client_key'],
            'certfile': settings.BROKER['ssl_client_certificate'],
            'cert_reqs': ssl.CERT_REQUIRED,
        }
        celery.conf.update(BROKER_USE_SSL=BROKER_USE_SSL)

configure_SSL()
configure_login_method()
