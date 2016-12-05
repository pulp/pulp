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

from pulp.common import TASK_INCOMPLETE_STATES
from pulp.tasking.constants import TASKING_CONSTANTS
from pulp.tasking.util import cancel

_logger = logging.getLogger(__name__)


def _parse_and_log_event(event):
    """
    Parse and return the event information we are interested in. Also log it.

    A new dict is returned containing the keys 'timestamp', 'local_received', 'type', and
    'worker_name'. The data transformations here are on the timestamp and local_received. They
    both arrive as seconds since the epoch, and are converted to a naive datetime.datetime object in
    UTC. The timestamp is set by the sender, and the local_received time is set by the receiver.
    Beware of a bug in the value of the timestamp as of the time of this commit as it suffers from
    issues in localities that use daylight savings time during the non-daylight savings time part of
    the year. See https://github.com/celery/celery/issues/1802#issuecomment-161916587 for discussion
    around this issue. Until that issue is resolved, consider using the local_received time instead
    of the timestamp.

    Logging is done through a call to _log_event().

    :param event: A celery event
    :type  event: dict
    :return:      A dict containing the keys 'timestamp', 'local_received', 'type', and
                  'worker_name'. 'timestamp' and 'local_received' are naive datetime.datetime
                  objects reported in UTC. 'type' is the event name as a string
                  (ie: 'worker-heartbeat'), and 'worker_name' is the name of the worker as a string.
    :rtype:       dict
    """
    event_info = {
        'timestamp': datetime.utcfromtimestamp(event['timestamp']),
        'local_received': datetime.utcfromtimestamp(event['local_received']), 'type': event['type'],
        'worker_name': event['hostname']}
    msg = _("'%(type)s' sent at time %(timestamp)s from %(worker_name)s, received at time: "
            "%(local_received)s")
    msg = msg % event_info
    _logger.debug(msg)
    return event_info


def handle_worker_heartbeat(event):
    """
    Celery event handler for 'worker-heartbeat' events.

    The event is first parsed and logged.  Then the existing Worker objects are
    searched for one to update. If an existing one is found, it is updated.
    Otherwise a new Worker entry is created. Logging at the info and debug
    level is also done.

    :param event: A celery event to handle.
    :type event: dict
    """
    from pulp.app.models import Worker

    event_info = _parse_and_log_event(event)
    existing_worker, created = Worker.objects.get_or_create(name=event_info['worker_name'])
    if created:
        msg = _("New worker '%(worker_name)s' discovered") % event_info
        _logger.info(msg)
    else:
        existing_worker.save_heartbeat()


def handle_worker_offline(event):
    """
    Celery event handler for 'worker-offline' events.

    The 'worker-offline' event is emitted when a worker gracefully shuts down. It is not
    emitted when a worker is killed instantly.

    The event is first parsed and logged. If this event is from the resource manager, there is
    no further processing to be done. Otherwise, a worker is shutting down, and a
    delete_worker() task is dispatched so that the resource manager will remove the record,
    and handle any work cleanup associated with a worker going offline. Logging at the info
    and debug level is also done.

    :param event: A celery event to handle.
    :type event: dict
    """
    event_info = _parse_and_log_event(event)

    msg = _("Worker '%(worker_name)s' shutdown") % event_info
    _logger.info(msg)
    delete_worker(event_info['worker_name'], normal_shutdown=True)


def delete_worker(name, normal_shutdown=False):
    """
    Delete the :class:`~pulp.app.models.Worker` from the database and cancel associated tasks.

    If the worker shutdown normally, no message is logged, otherwise an error level message is
    logged. Default is to assume the worker did not shut down normally.

    Any resource reservations associated with this worker are cleaned up by this function.

    Any tasks associated with this worker are explicitly canceled.

    :param name:            The name of the worker you wish to delete.
    :type  name:            basestring
    :param normal_shutdown: True if the worker shutdown normally, False otherwise. Defaults to
                            False.
    :type normal_shutdown:  bool
    """
    from pulp.app.models import Worker, TaskLock

    if not normal_shutdown:
        msg = _('The worker named %(name)s is missing. Canceling the tasks in its queue.')
        msg = msg % {'name': name}
        _logger.error(msg)

    try:
        worker = Worker.objects.get(name=name)
    except Worker.DoesNotExist:
        pass
    else:
        # Cancel all of the tasks that were assigned to this worker's queue
        for task_status in worker.tasks.filter(state__in=TASK_INCOMPLETE_STATES):
            cancel(task_status.pk)

        worker.delete()

    is_resource_manager = name.startswith(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME)
    is_celerybeat = name.startswith(TASKING_CONSTANTS.CELERYBEAT_WORKER_NAME)
    if is_celerybeat or is_resource_manager:
        TaskLock.objects.filter(name=name).delete()
