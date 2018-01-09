"""
A module designed to handle celery events related to workers.

Two celery events that need processing are the 'worker-heartbeat' and 'worker-offline'
events. Each 'worker-heartbeat' event is passed to handle_worker_heartbeat() as an event for
handling. Each 'worker-offline' event is passed to handle_worker_offline() for handling.
See the individual function docblocks for more detail on how each event type is handled.

The use of an 'event' or 'celery event' throughout this module refers to a dict built by celery
that contains event information. Read more about this in the docs for celery.events.

Other functions in this module are helper functions designed to deduplicate the amount of shared
code between the event handlers.
"""

from datetime import datetime, timedelta
from gettext import gettext as _
import logging

from pulp.server.async.tasks import _delete_worker
from pulp.server.constants import PULP_PROCESS_HEARTBEAT_INTERVAL
from pulp.server.db.model import Worker


_logger = logging.getLogger(__name__)


def handle_worker_heartbeat(worker_name):
    """
    This is a generic function for updating worker heartbeat records.

    Existing Worker objects are searched for one to update. If an existing one is found, it is
    updated. Otherwise a new Worker entry is created. Logging at the info level is also done.

    :param worker_name: The hostname of the worker
    :type  worker_name: basestring
    """
    start = datetime.utcnow()
    existing_worker = Worker.objects(name=worker_name).first()

    if not existing_worker:
        msg = _("New worker '%s' discovered") % worker_name
        _logger.info(msg)

    timestamp = datetime.utcnow()
    msg = _("Worker heartbeat from '{name}' at time {timestamp}").format(timestamp=timestamp,
                                                                         name=worker_name)
    _logger.debug(msg)

    Worker.objects(name=worker_name).update_one(set__last_heartbeat=timestamp,
                                                upsert=True)

    if(datetime.utcnow() - start > timedelta(seconds=PULP_PROCESS_HEARTBEAT_INTERVAL)):
        sec = (datetime.utcnow() - start).total_seconds()
        msg = _("Worker {name} heartbeat time {time}s exceeds heartbeat interval. Consider "
                "adjusting the worker_timeout setting.").format(time=sec, name=worker_name)
        _logger.warn(msg)


def handle_worker_offline(worker_name):
    """
    This is a generic function for handling workers going offline.

    _delete_worker() task is called to handle any work cleanup associated with a worker going
    offline. Logging at the info level is also done.

    :param worker_name: The hostname of the worker
    :type  worker_name: basestring
    """
    msg = _("Worker '%s' shutdown") % worker_name
    _logger.info(msg)
    _delete_worker(worker_name, normal_shutdown=True)
