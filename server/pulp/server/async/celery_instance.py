"""
Due to our factory, we cannot put the instantiation of the Celery application into our app.py
module, as it will lead to circular dependencies since tasks.py also need to import this object, and
the factory ends up importing tasks.py when it imports all the managers.

Hopefully we will eliminate the factory in the future, but until then this workaround is necessary.
"""
from datetime import timedelta
import ssl

from celery import Celery

from pulp.server.config import config


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
}


def create_mongo_config():
    """
    Inspects the pulp config's mongodb settings and returns a data structure
    that can be passed to celery for it's mongodb result backend config.

    :return:    dictionary with keys 'host' and 'database', and optionally with
                keys 'user' and 'password', that can be passed to celery as the
                config for a mongodb result backend
    :rtype:     dict
    """
    db_name = config.get('database', 'name')

    # celery 3.1 doesn't support multiple seeds, so we just use the first one
    seeds = config.get('database', 'seeds')
    seed = seeds.split(',')[0].strip()
    host = seed.split(':')[0]
    port = seed.split(':')[1] if ':' in seed else None
    mongo_config = {'host': host, 'database': db_name}
    if port:
        mongo_config['port'] = port
    if config.has_option('database', 'username') and config.has_option('database', 'password'):
        mongo_config['user'] = config.get('database', 'username')
        mongo_config['password'] = config.get('database', 'password')
    if config.getboolean('database', 'ssl'):
        mongo_config['ssl'] = True
        ssl_keyfile = config.get('database', 'ssl_keyfile')
        ssl_certfile = config.get('database', 'ssl_certfile')
        if ssl_keyfile:
            mongo_config['ssl_keyfile'] = ssl_keyfile
        if ssl_certfile:
            mongo_config['ssl_certfile'] = ssl_certfile
        verify_ssl = config.getboolean('database', 'verify_ssl')
        mongo_config['ssl_cert_reqs'] = ssl.CERT_REQUIRED if verify_ssl else ssl.CERT_NONE
        mongo_config['ssl_ca_certs'] = config.get('database', 'ca_path')
    return mongo_config


celery.conf.update(CELERYBEAT_SCHEDULE=CELERYBEAT_SCHEDULE)
celery.conf.update(CELERYBEAT_SCHEDULER='pulp.server.async.scheduler.Scheduler')
celery.conf.update(CELERY_RESULT_BACKEND='mongodb')
celery.conf.update(CELERY_MONGODB_BACKEND_SETTINGS=create_mongo_config())
celery.conf.update(CELERY_WORKER_DIRECT=True)


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
