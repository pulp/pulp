"""
Manager to return status information about a running Pulp instance
"""
from logging import getLogger
from pkg_resources import get_distribution

from pulp.server.async.celery_instance import celery
from pulp.server.db import connection
from pulp.server.db.model import Worker


_logger = getLogger(__name__)


def get_version():
    """
    :returns:          Pulp platform version
    :rtype:            str
    """
    return {'platform_version': get_distribution("pulp-server").version}


def get_workers():
    """
    :returns:          list of workers with their heartbeats
    :rtype:            list
    """
    return Worker.objects()


def get_mongo_conn_status():
    """
    Perform a simple mongo operation and return success or failure.

    This uses a "raw" pymongo Collection to avoid any auto-retry logic.

    :returns:          mongo connection status
    :rtype:            bool
    """
    try:
        db = connection.get_database()
        db.workers.count()
        return {'connected': True}
    except:
        return {'connected': False}


def get_broker_conn_status():
    """
    :returns:          message broker connection status
    :rtype:            bool
    """
    # not all drivers support heartbeats. For now, we need to make an
    # explicit connection and then release it.
    # See https://github.com/celery/kombu/issues/432 for more detail.
    try:
        conn = celery.connection()
        conn.connect()
        conn.release()
        return {'connected': True}
    except Exception:
        _logger.exception('Connection to broker failed during status check!')
        # if the above was not successful for any reason, return False
        return {'connected': False}
