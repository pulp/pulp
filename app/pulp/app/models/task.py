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
from pulp.exceptions import exception_to_dict


_logger = logging.getLogger(__name__)


class ReservedResource(Model):
    """
    Resources that have been reserved

    Fields:

        resource (models.TextField): The name of the resource reserved for the task.

    Relations:

        task (models.ForeignKey): The task associated with this reservation
        worker (models.ForeignKey): The worker associated with this reservation
    """
    resource = models.TextField()

    task = models.OneToOneField("Task")
    worker = models.ForeignKey("Worker", on_delete=models.CASCADE, related_name="reservations")


class WorkerManager(models.Manager):

    def get_unreserved_worker(self):
        """
        Randomly selects an unreserved :class:`~pulp.app.models.Worker`

        Return the Worker instance that has no :class:`~pulp.app.models.ReservedResource`
        associated with it. If all workers have ReservedResource relationships, a
        :class:`pulp.app.models.Worker.DoesNotExist` exception is raised.

        This method also provides randomization for worker selection.

        :raises Worker.DoesNotExist: If all workers have ReservedResource entries associated with
                                     them.

        :returns:          A randomly-selected Worker instance that has no ReservedResource
                           entries associated with it.
        :rtype:            pulp.app.models.Worker
        """
        free_workers_qs = self.annotate(models.Count('reservations')).filter(reservations__count=0)
        if free_workers_qs.count() == 0:
            raise self.model.DoesNotExist()
        return free_workers_qs.order_by('?').first()


class Worker(Model):
    """
    Represents a worker

    Fields:

        name (models.TextField): The name of the worker, in the format "worker_type@hostname"
        last_heartbeat (models.DateTimeField): A timestamp of this worker's last heartbeat
    """
    objects = WorkerManager()

    name = models.TextField(db_index=True, unique=True)
    last_heartbeat = models.DateTimeField(auto_now=True)

    def save_heartbeat(self):
        """Save a worker heartbeat

        Update the last_heartbeat field to now and save it.

        Warning:

            Only the last_heartbeat field will be saved. No other changes will be saved.
        """
        self.save(update_fields=['last_heartbeat'])


class TaskLock(Model):
    """
    Locking mechanism for services that utilize active/passive fail-over

    Fields:

        name (models.TextField): The name of the item that has the lock
        timestamp (models.DateTimeField): The time the lock was acquired
        lock (models.TextField): The name of the lock acquired

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

        group (models.UUIDField): The group this task belongs to
        state (models.TextField): The state of the task
        started_at (models.DateTimeField): The time the task started executing
        finished_at (models.DateTimeField): The time the task finished executing
        non_fatal_errors (pulp.app.fields.JSONField): Dictionary of non-fatal errors that occurred
            while task was running.
        result (pulp.app.fields.JSONField): Return value of the task

    Relations:

        parent (models.ForeignKey): Task that spawned this task (if any)
        worker (models.ForeignKey): The worker that this task is in
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

    non_fatal_errors = JSONField(default=list)
    result = JSONField(null=True)

    parent = models.ForeignKey("Task", null=True, related_name="spawned_tasks")
    worker = models.ForeignKey("Worker", null=True, related_name="tasks")

    def set_running(self):
        """
        Set this Task to the running state, save it, and log output in warning cases.

        This updates the :attr:`started_at` and sets the :attr:`state` to :attr:`RUNNING`.
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

        This updates the :attr:`finished_at` and sets the :attr:`state` to :attr:`COMPLETED`.

        Args:
            result (dict): The result to save on the :class:`~pulp.app.models.Task`
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

        This updates the :attr:`finished_at` attribute, sets the :attr:`state` to
        :attr:`FAILED`, and sets the :attr:`result` attribute.

        Args:
            exc (Exception): The exception raised by the task.
            einfo (celery.datastructures.ExceptionInfo): ExceptionInfo instance containing a
                serialized traceback.
        """
        self.state = Task.FAILED
        self.finished_at = timezone.now()
        self.result = exception_to_dict(exc, einfo.traceback)
        self.save()


class TaskTag(Model):
    """
    Custom tags for a task

    Fields:

        name (models.TextField): The name of the tag

    Relations:

        task (models.ForeignKey): The task this tag is associated with
    """
    name = models.TextField()

    task = models.ForeignKey("Task", related_name="tags", related_query_name="tag")
