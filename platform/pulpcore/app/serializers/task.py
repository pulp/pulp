from gettext import gettext as _

from rest_framework import serializers

from pulpcore.app import models
from pulpcore.app.serializers import ModelSerializer, ProgressReportSerializer


class TaskTagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        help_text=_("The name of the tag")
    )

    class Meta:
        model = models.TaskTag
        fields = ('name',)


class TaskSerializer(ModelSerializer):
    _href = serializers.HyperlinkedIdentityField(
        view_name='tasks-detail',
    )

    group = serializers.UUIDField(
        help_text=_("The group that this task belongs to."),
        read_only=True
    )

    state = serializers.CharField(
        help_text=_("The current state of the task. The possible values include:"
                    " 'waiting', 'skipped', 'running', 'completed', 'failed' and 'canceled'."),
        read_only=True
    )

    started_at = serializers.DateTimeField(
        help_text=_("Timestamp of the when this task started execution."),
        read_only=True
    )

    finished_at = serializers.DateTimeField(
        help_text=_("Timestamp of the when this task stopped execution."),
        read_only=True
    )

    non_fatal_errors = serializers.JSONField(
        help_text=_("A JSON Object of non-fatal errors encountered during the execution of this "
                    "task."),
        read_only=True
    )

    error = serializers.JSONField(
        help_text=_("A JSON Object of a fatal error encountered during the execution of this "
                    "task."),
        read_only=True
    )

    worker = serializers.HyperlinkedRelatedField(
        help_text=_("The worker associated with this task."
                    " This field is empty if a worker is not yet assigned."),
        read_only=True,
        view_name='workers-detail',
        lookup_field='name'
    )

    parent = serializers.HyperlinkedRelatedField(
        help_text=_("The parent task that spawned this task."),
        read_only=True,
        view_name='tasks-detail'
    )

    tags = TaskTagSerializer(
        many=True,
        read_only=True
    )

    progress_reports = ProgressReportSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = models.Task
        fields = ModelSerializer.Meta.fields + ('group', 'state', 'started_at',
                                                'finished_at', 'non_fatal_errors',
                                                'error', 'worker', 'parent', 'tags',
                                                'progress_reports')


class WorkerSerializer(ModelSerializer):
    _href = serializers.HyperlinkedIdentityField(
        view_name='workers-detail',
        lookup_field='name'
    )

    name = serializers.CharField(
        help_text=_('The name of the worker.'),
        read_only=True
    )

    last_heartbeat = serializers.DateTimeField(
        help_text=_('Timestamp of the last time the worker talked to the service.'),
        read_only=True
    )

    online = serializers.BooleanField(
        help_text='Whether the worker is online or not. Defaults to True.',
        read_only=True
    )

    class Meta:
        model = models.Worker
        fields = ModelSerializer.Meta.fields + ('name', 'last_heartbeat', 'online')
