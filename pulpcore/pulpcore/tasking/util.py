from contextlib import suppress
from gettext import gettext as _
import logging

from celery import current_app, current_task
from celery.app import control

from pulpcore.app.models import Task
from pulpcore.common import TASK_FINAL_STATES
from pulpcore.exceptions import MissingResource


celery_controller = control.Control(app=current_app)
_logger = logging.getLogger(__name__)


def cancel(task_id):
    """
    Cancel the task that is represented by the given task_id.

    This method cancels only the task with given task_id, not the spawned tasks. This also updates
    task's state to 'canceled'.

    :param task_id: The ID of the task you wish to cancel
    :type  task_id: basestring

    :raises MissingResource: if a task with given task_id does not exist
    """
    try:
        task_status = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise MissingResource(task_id)

    if task_status.state in TASK_FINAL_STATES:
        # If the task is already done, just stop
        msg = _('Task [%(task_id)s] already in a completed state: %(state)s')
        _logger.info(msg % {'task_id': task_id, 'state': task_status.state})
        return

    celery_controller.revoke(task_id, terminate=True)
    task_status.state = Task.CANCELED
    task_status.save()

    msg = _('Task canceled: %(task_id)s.')
    msg = msg % {'task_id': task_id}
    _logger.info(msg)


def get_current_task_id():
    """"
    Get the current task id from celery. If this is called outside of a running
    celery task it will return None

    :return: The ID of the currently running celery task or None if not in a task
    :rtype: str
    """
    with suppress(AttributeError):
        return current_task.request.id
