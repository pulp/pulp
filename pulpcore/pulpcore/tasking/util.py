from contextlib import suppress
from gettext import gettext as _
import logging

from celery import current_app, current_task
from celery.app import control

from django.db import transaction
from django.urls import reverse

from pulpcore.app.models import Task
from pulpcore.app.serializers import view_name_for_model
from pulpcore.common import TASK_FINAL_STATES, TASK_STATES
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

    with transaction.atomic():
        task_status.state = TASK_STATES.CANCELED
        task_status.save()
        _delete_incomplete_resources(task_status)

    msg = _('Task canceled: %(task_id)s.')
    msg = msg % {'task_id': task_id}
    _logger.info(msg)


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
            _logger.error(
                _('Delete created resource, failed: %(reason)s'),
                {
                    'reason': str(error)
                })


def get_current_task_id():
    """"
    Get the current task id from celery. If this is called outside of a running
    celery task it will return None

    :return: The ID of the currently running celery task or None if not in a task
    :rtype: str
    """
    with suppress(AttributeError):
        return current_task.request.id


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
