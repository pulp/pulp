"""
Django models related to the Tasking system
"""
from django.db import models

from pulp.app.models import Model
from pulp.app.fields import JSONField


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
    ACCEPTED = 'accepted'
    RUNNING = 'running'
    SUSPENDED = 'suspended'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELED = 'canceled'
    STATES = (
        (WAITING, 'Waiting'),
        (SKIPPED, 'Skipped'),
        (ACCEPTED, 'Accepted'),
        (RUNNING, 'Running'),
        (SUSPENDED, 'Suspended'),
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


class ScheduledCalls(Model):
    """
    Scheduled Call Request

    Fields:

    :cvar task: The task that should be run on a schedule
    :type task: models.TextField

    :cvar enabled: Indicates if schedule should be actively run by the scheduler
    :type enabled: models.BooleanField

    :cvar resource: Indicates a unique resource that should be used to find this schedule
    :type resource: models.TextField

    :cvar iso_schedule: ISO8601 string representing the schedule
    :type iso_schedule: models.TextField

    :cvar schedule: Pickled instance of celery.schedules.schedule that should be run.
    :type schedule: models.TextField

    :cvar first_run: The first time this schedule was ran
    :type first_run: models.DateTimeField

    :cvar last_run: Last time this schedule was ran
    :type last_run: models.DateTimeField

    :cvar total_run_count: Number of times this schedle has ran
    :type total_run_count: models.IntegerField

    :cvar last_updated: The last time this schedule was saved to the database
    :type last_updated: models.DateTimeField

    :cvar args: Arguments that should be passed to the apply_async function
    :type args: models.JSONField

    :cvar kwargs: Keyword arguments that should be passed to the apply_async function
    :type kwargs: models.JSONField
    """
    task = models.TextField()
    enabled = models.BooleanField(default=True)
    resource = models.TextField(null=True)

    iso_schedule = models.TextField()
    schedule = models.TextField(null=True)

    first_run = models.DateTimeField()
    last_run = models.DateTimeField(null=True)
    total_run_count = models.IntegerField()

    last_updated = models.DateTimeField()

    args = JSONField()
    kwargs = JSONField()
