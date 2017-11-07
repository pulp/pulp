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

from datetime import timedelta
from django.utils import timezone
from gettext import gettext as _
import logging

from pulpcore.app.models import Worker, TaskLock
from pulpcore.common import TASK_INCOMPLETE_STATES
from pulpcore.tasking.constants import TASKING_CONSTANTS
from pulpcore.tasking.util import cancel


_logger = logging.getLogger(__name__)


def handle_worker_heartbeat(worker_name):
    """
    This is a generic function for updating worker heartbeat records.

    Existing Worker objects are searched for one to update. If an existing one is found, it is
    updated. Otherwise a new Worker entry is created. Logging at the info level is also done.

    :param worker_name: The hostname of the worker
    :type  worker_name: basestring
    """
    existing_worker, created = Worker.objects.get_or_create(name=worker_name)
    if created:
        msg = _("New worker '{name}' discovered").format(name=worker_name)
        _logger.info(msg)
    elif existing_worker.online is False:
        msg = _("Worker '{name}' is back online.").format(name=worker_name)
        _logger.info(msg)
        existing_worker.online = True
        existing_worker.save()
    else:
        existing_worker.save_heartbeat()

    msg = _("Worker heartbeat from '{name}' at time {timestamp}").format(
        timestamp=existing_worker.last_heartbeat,
        name=worker_name
    )

    _logger.debug(msg)


def check_celery_processes():
    """
    Look for missing Celery processes, log and cleanup as needed.

    To find a missing Celery process, filter the Workers model for entries older than
    utcnow() - WORKER_TIMEOUT_SECONDS. The heartbeat times are stored in native UTC, so this is
    a comparable datetime. For each missing worker found, call mark_worker_offline()
    synchronously for cleanup.

    This method also checks that at least one resource_manager and one worker process is
    present. If there are zero of either, log at the error level that Pulp will not operate
    correctly.
    """
    msg = _('Checking if pulp_workers or pulp_resource_manager processes are '
            'missing for more than %d seconds') % TASKING_CONSTANTS.PULP_PROCESS_TIMEOUT_INTERVAL
    _logger.debug(msg)
    now = timezone.now()
    oldest_heartbeat_time = now - timedelta(seconds=TASKING_CONSTANTS.PULP_PROCESS_TIMEOUT_INTERVAL)

    for worker in Worker.objects.filter(last_heartbeat__lt=oldest_heartbeat_time, online=True):
        msg = _("Worker '%s' has gone missing, removing from list of workers") % worker.name
        _logger.error(msg)

        mark_worker_offline(worker.name)

    worker_count = Worker.objects.exclude(
        name__startswith=TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME).filter(online=True).count()

    resource_manager_count = Worker.objects.filter(
        name__startswith=TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME).filter(online=True).count()

    if resource_manager_count == 0:
        msg = _("There are 0 pulp_resource_manager processes running. Pulp will not operate "
                "correctly without at least one pulp_resource_mananger process running.")
        _logger.error(msg)

    if worker_count == 0:
        msg = _("There are 0 worker processes running. Pulp will not operate "
                "correctly without at least one worker process running.")
        _logger.error(msg)

    output_dict = {'workers': worker_count, 'resource_manager': resource_manager_count}
    msg = _("%(workers)d pulp_worker processes and %(resource_manager)d "
            "pulp_resource_manager processes") % output_dict
    _logger.debug(msg)


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
    mark_worker_offline(worker_name, normal_shutdown=True)


def mark_worker_offline(name, normal_shutdown=False):
    """
    Mark the :class:`~pulpcore.app.models.Worker` as offline and cancel associated tasks.

    If the worker shutdown normally, no message is logged, otherwise an error level message is
    logged. Default is to assume the worker did not shut down normally.

    Any resource reservations associated with this worker are cleaned up by this function.

    Any tasks associated with this worker are explicitly canceled.

    :param name:            The name of the worker you wish to be marked as offline.
    :type  name:            basestring
    :param normal_shutdown: True if the worker shutdown normally, False otherwise. Defaults to
                            False.
    :type normal_shutdown:  bool
    """
    is_resource_manager = name.startswith(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME)

    if not normal_shutdown:
        msg = _('The worker named %(name)s is missing. Canceling the tasks in its queue.')
        msg = msg % {'name': name}
        _logger.error(msg)
    else:
        msg = _("Cleaning up shutdown worker '%s'.") % name
        _logger.info(msg)

    try:
        worker = Worker.objects.get(name=name, online=True)
    except Worker.DoesNotExist:
        pass
    else:
        # Cancel all of the tasks that were assigned to this worker's queue
        for task_status in worker.tasks.filter(state__in=TASK_INCOMPLETE_STATES):
            cancel(task_status.pk)
        worker.online = False
        worker.save()

    if is_resource_manager:
        TaskLock.objects.filter(name=name).delete()
