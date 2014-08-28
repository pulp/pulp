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
        'task': 'pulp.server.db.reaper.reap_expired_documents',
        'schedule': timedelta(days=config.getfloat('data_reaping', 'reaper_interval')),
        'args': tuple(),
    },
    'monthly_maintenance': {
        'task': 'pulp.server.maintenance.monthly.monthly_maintenance',
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
    if config.has_option('database', 'user') and config.has_option('database', 'password'):
        mongo_config['user'] = config.get('database', 'user')
        mongo_config['password'] = config.get('database', 'password')
    return mongo_config


celery.conf.update(CELERYBEAT_SCHEDULE=CELERYBEAT_SCHEDULE)
celery.conf.update(CELERYBEAT_SCHEDULER='pulp.server.async.scheduler.Scheduler')
celery.conf.update(CELERY_RESULT_BACKEND='mongodb')
celery.conf.update(CELERY_MONGODB_BACKEND_SETTINGS=create_mongo_config())
celery.conf.update(CELERY_WORKER_DIRECT=True)

if config.getboolean('tasks', 'celery_require_ssl'):
    BROKER_USE_SSL = {
        'ca_certs': config.get('tasks', 'cacert'),
        'keyfile': config.get('tasks', 'keyfile'),
        'certfile': config.get('tasks', 'certfile'),
        'cert_reqs': ssl.CERT_REQUIRED,
    }
    celery.conf.update(BROKER_USE_SSL=BROKER_USE_SSL)
