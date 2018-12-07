from gettext import gettext as _
import logging
import time

from django.db import transaction
from django.urls import reverse
from rq.job import Job

from pulpcore.app.models import Task
from pulpcore.app.serializers import view_name_for_model
from pulpcore.constants import TASK_FINAL_STATES, TASK_STATES
from pulpcore.exceptions import MissingResource
from pulpcore.tasking import connection
from pulpcore.tasking.constants import TASKING_CONSTANTS


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
        raise MissingResource(task=task_id)

    if task_status.state in TASK_FINAL_STATES:
        # If the task is already done, just stop
        msg = _('Task [{task_id}] already in a completed state: {state}')
        _logger.info(msg.format(task_id=task_id, state=task_status.state))
        return

    redis_conn = connection.get_redis_connection()
    job = Job(id=str(task_id), connection=redis_conn)

    if job.is_started:
        redis_conn.sadd(TASKING_CONSTANTS.KILL_KEY, job.get_id())
    job.delete()

    # A hack to ensure that we aren't deleting resources still being used by the workhorse
    time.sleep(1.5)

    with transaction.atomic():
        task_status.state = TASK_STATES.CANCELED
        task_status.save()
        _delete_incomplete_resources(task_status)

    _logger.info(_('Task canceled: {id}.').format(id=task_id))


def _delete_incomplete_resources(task):
    """
    Delete all incomplete created-resources on a canceled task.

    Args:
        task (Task): A task.
    """
    if not task.state == TASK_STATES.CANCELED:
        raise RuntimeError(_('Task must be canceled.'))
    for model in (r.content_object for r in task.created_resources.all()):
        try:
            if model.complete:
                continue
        except AttributeError:
            continue
        try:
            with transaction.atomic():
                model.delete()
        except Exception as error:
            _logger.error(_('Delete created resource, failed: {}').format(str(error)))


def get_url(model):
    """
    Get a resource url for the specified model object. This returns the path component of the
    resource URI.  This is used in our resource locking/reservation code to identify resources.

    Args:
        model (django.models.Model): A model object.

    Returns:
        str: The path component of the resource url
    """
    return reverse(view_name_for_model(model, 'detail'), args=[model.pk])
