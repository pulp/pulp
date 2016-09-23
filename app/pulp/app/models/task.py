"""
Django models related to the Tasking system
"""
from gettext import gettext as _
import logging

from django.db import models
from django.utils import timezone

from pulp.app.models import Model
from pulp.app.fields import JSONField
from pulp.common import TASK_FINAL_STATES
from pulp.exceptions import PulpException


_logger = logging.getLogger(__name__)


class ReservedResource(Model):
    """
    Resources that have been reserved

    Fields:

    :cvar resource: The name of the resource reserved for the task.
    :type resource: models.TextField

    Relations:

    :cvar task: The task associated with this reservation
    :type task: models.ForeignKey

    :cvar worker: The worker associated with this reservation
    :type worker: models.ForeignKey
    """
    resource = models.TextField()

    task = models.OneToOneField("Task")
    worker = models.ForeignKey("Worker", on_delete=models.CASCADE, related_name="reservations")


class Worker(Model):
    """
    Represents a worker

    Fields:

    :cvar name: The name of the worker, in the format "worker_type@hostname"
    :type name: models.TextField

    :cvar last_heartbeat: A timestamp of this worker's last heartbeat
    :type last_heartbeat: models.DateTimeField
    """
    name = models.TextField(db_index=True, unique=True)
    last_heartbeat = models.DateTimeField(auto_now=True)

    def save_heartbeat(self):
        """Save a worker heartbeat

        Update the last_heartbeat field to now and save it.

        !!! Only the last_heartbeat field will be saved. No other changes will be saved.
        """
        self.save(update_fields=['last_heartbeat'])


class TaskLock(Model):
    """
    Locking mechanism for services that utilize active/passive fail-over

    Fields:

    :cvar name: The name of the item that has the lock
    :type name: models.TextField

    :cvar timestamp: The time the lock was acquired
    :type timestamp: models.DateTimeField

    :cvar lock: The name of the lock acquired
    :type lock: models.TextField

    """
    CELERY_BEAT = 'CeleryBeat'
    RESOURCE_MANAGER = 'ResourceManager'
    LOCK_STRINGS = (
        (CELERY_BEAT, 'Celery Beat Lock'),
        (RESOURCE_MANAGER, 'Resource Manager Lock')
    )

    name = models.TextField(db_index=True, unique=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    lock = models.TextField(unique=True, null=False, choices=LOCK_STRINGS)


class Task(Model):
    """
    Represents a task

    Fields:

    :cvar group: The group this task belongs to
    :type group: models.UUIDField

    :cvar state: The state of the task
    :type state: models.TextField

    :cvar started_at: The time the task started executing
    :type started_at: models.DateTimeField

    :cvar finished_at: The time the task finished executing
    :type finished_at: models.DateTimeField

    :cvar non_fatal_errors: Dictionary of non-fatal errors that occurred while task was running.
    :type non_fatal_errors: models.JSONField

    :cvar result: Return value of the task
    :type result: models.JSONField

    Relations:

    :cvar parent: Task that spawned this task (if any)
    :type parent: models.ForeignKey

    :cvar worker: The worker that this task is in
    :type worker: models.ForeignKey
    """

    WAITING = 'waiting'
    SKIPPED = 'skipped'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELED = 'canceled'
    STATES = (
        (WAITING, 'Waiting'),
        (SKIPPED, 'Skipped'),
        (RUNNING, 'Running'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (CANCELED, 'Canceled')
    )
    group = models.UUIDField(null=True)
    state = models.TextField(choices=STATES)

    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)

    non_fatal_errors = JSONField()
    result = JSONField()

    parent = models.ForeignKey("Task", null=True, related_name="spawned_tasks")
    worker = models.ForeignKey("Worker", null=True, related_name="tasks")

    def set_running(self):
        """
        Set this Task to the running state, save it, and log output in warning cases.

        This updates the :attr: `started_at` and sets the :attr: `state` to :attr: `RUNNING`.
        """
        if self.state != self.WAITING:
            msg = _('Task __call__() occurred but Task %s is not at WAITING')
            _logger.warning(msg % self.request.id)
        self.state = Task.RUNNING
        self.started_at = timezone.now()
        self.save()

    def set_completed(self, result):
        """
        Set this Task to the completed state, save it, and log output in warning cases.

        This updates the :attr: `finished_at` and sets the :attr: `state` to :attr: `COMPLETED`.

        :param result: The result to save on the :class: `~pulp.app.models.Task`
        :type result: dict
        """
        self.finished_at = timezone.now()
        self.result = result

        # Only set the state to finished if it's not already in a complete state. This is
        # important for when the task has been canceled, so we don't move the task from canceled
        # to finished.
        if self.state not in TASK_FINAL_STATES:
            self.state = Task.COMPLETED
        else:
            msg = _('Task set_completed() occurred but Task %s is already in final state')
            _logger.warning(msg % self.pk)

        self.save()

    def set_failed(self, exc, einfo):
        """
        Set this Task to the failed state and save it.

        This updates the :attr: `finished_at` attribute, sets the :attr: `state` to
        :attr: `FAILED`, and sets the :attr: `result` attribute.

        :param exc:     The exception raised by the task.
        :type exc:      ???

        :param einfo:   celery's ExceptionInfo instance, containing serialized traceback.
        :type einfo:    ???
        """
        self.state = Task.FAILED
        self.finished_at = timezone.now()
        if isinstance(exc, PulpException):
            self.result = exc.to_dict()
        else:
            self.result = {'traceback': einfo.traceback}
        self.save()


class TaskTag(Model):
    """
    Custom tags for a task

    Fields:

    :cvar name: The name of the tag
    :type name: models.TextField

    Relations:

    :cvar task: The task this tag is associated with
    :type task: models.ForeignKey
    """
    name = models.TextField()

    task = models.ForeignKey("Task", related_name="tags", related_query_name="tag")
