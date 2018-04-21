import os
import ssl

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'pulpcore.app.settings')

from django.conf import settings  # noqa

broker_url = settings.BROKER['url']
celery = Celery('tasks', broker=broker_url)


DEDICATED_QUEUE_EXCHANGE = 'C.dq2'
RESOURCE_MANAGER_QUEUE = 'resource_manager'
CELERYBEAT_SCHEDULE = {
}


celery.conf.update(beat_schedule=CELERYBEAT_SCHEDULE)
celery.conf.update(worker_direct=True)
celery.conf.update(task_serializer='json')
celery.conf.update(accept_content=['json'])
celery.conf.update(task_reject_on_worker_lost=True)


def configure_login_method():
    """
    Configures the celery object with broker_login_method if not default.
    """
    login_method = settings.BROKER['login_method']
    if login_method is not None:
        celery.conf.update(broker_login_method=login_method)


def configure_SSL():
    """
    Configures the celery object with broker_use_ssl options
    """
    if settings.BROKER['celery_require_ssl']:
        BROKER_USE_SSL = {
            'ca_certs': settings.BROKER['ssl_ca_certificate'],
            'keyfile': settings.BROKER['ssl_client_key'],
            'certfile': settings.BROKER['ssl_client_certificate'],
            'cert_reqs': ssl.CERT_REQUIRED,
        }
        celery.conf.update(broker_use_ssl=BROKER_USE_SSL)


configure_SSL()
configure_login_method()
