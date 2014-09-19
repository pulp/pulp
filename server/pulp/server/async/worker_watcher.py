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

from datetime import datetime
from gettext import gettext as _
import logging
import re

from pulp.server.async.celery_instance import RESOURCE_MANAGER_QUEUE
from pulp.server.async.tasks import _delete_worker
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.resources import Worker
from pulp.server.managers import resources


_logger = logging.getLogger(__name__)


def _is_resource_manager(event):
    """
    Determine if this event is for a resource manager.

    :param event: A celery event
    :type event: dict
    :return: True if this event is from a resource manager, False otherwise.
    :rtype: bool
    """
    if re.match('^%s' % RESOURCE_MANAGER_QUEUE, event['hostname']):
        return True
    else:
        return False


def _parse_and_log_event(event):
    """
    Parse and return the event information we are interested in. Also log it.

    A new dict is returned containing the keys 'timestamp', 'type', and 'worker_name'. The
    only data transformation here is on the timestamp. The timestamp arrives as seconds since
    the epoch, and is converted to UTC time, and returned as a naive datetime.datetime object.

    Logging is done through a call to _log_event()

    :param event: A celery event
    :type event: dict
    :return: A dict containing the keys 'timestamp', 'type', and 'worker_name'. 'timestamp'
             is a naive datetime.datetime reported in UTC. 'type' is the event name as a string
             (ie: 'worker-heartbeat'), and 'worker_name' is the name of the worker as a string.
    :rtype: dict
    """
    event_info = {'timestamp': datetime.utcfromtimestamp(event['timestamp']),
                  'type': event['type'],
                  'worker_name': event['hostname']}
    _log_event(event_info)
    return event_info


def _log_event(event_info):
    """
    Log the type, worker_name, and timestamp of an event at the debug log level.

    :param event_info: A dict expected to contain the keys 'type', 'worker_name', and
                       'timestamp'. The value of each key will be converted to a string and
                       included in the log output.
    :type event_info: dict
    """
    msg = _("received '%(type)s' from %(worker_name)s at time: %(timestamp)s") % event_info
    _logger.debug(msg)


def handle_worker_heartbeat(event):
    """
    Celery event handler for 'worker-heartbeat' events.

    The event is first parsed and logged. If this event is from the resource manager, there is
    no further processing to be done. Then the existing Worker objects are searched
    for one to update. If an existing one is found, it is updated. Otherwise a new
    Worker entry is created. Logging at the info and debug level is also done.

    :param event: A celery event to handle.
    :type event: dict
    """
    event_info = _parse_and_log_event(event)

    # if this is the resource_manager do nothing
    if _is_resource_manager(event):
        return

    find_worker_criteria = Criteria(filters={'_id': event_info['worker_name']},
                                    fields=('_id', 'last_heartbeat'))
    find_worker_list = list(resources.filter_workers(find_worker_criteria))

    if find_worker_list:
        Worker.get_collection().find_and_modify(
            query={'_id': event_info['worker_name']},
            update={'$set': {'last_heartbeat': event_info['timestamp']}}
        )
    else:
        new_worker = Worker(event_info['worker_name'], event_info['timestamp'])
        msg = _("New worker '%(worker_name)s' discovered") % event_info
        _logger.info(msg)
        new_worker.save()


def handle_worker_offline(event):
    """
    Celery event handler for 'worker-offline' events.

    The 'worker-offline' event is emitted when a worker gracefully shuts down. It is not
    emitted when a worker is killed instantly.

    The event is first parsed and logged. If this event is from the resource manager, there is
    no further processing to be done. Otherwise, a worker is shutting down, and a
    _delete_worker() task is dispatched so that the resource manager will remove the record,
    and handle any work cleanup associated with a worker going offline. Logging at the info
    and debug level is also done.

    :param event: A celery event to handle.
    :type event: dict
    """
    event_info = _parse_and_log_event(event)

    # if this is the resource_manager do nothing
    if _is_resource_manager(event):
        return

    msg = _("Worker '%(worker_name)s' shutdown") % event_info
    _logger.info(msg)
    _delete_worker(event_info['worker_name'], normal_shutdown=True)
