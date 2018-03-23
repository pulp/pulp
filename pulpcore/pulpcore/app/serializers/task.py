from gettext import gettext as _

from rest_framework import serializers

from pulpcore.app import models
from pulpcore.app.serializers import ModelSerializer, ProgressReportSerializer, DetailIdentityField
from pulpcore.app.serializers import MasterModelSerializer

from .base import viewset_for_model

from pulpcore.app.models.task import CoreUpdateTask


class CreatedResourceSerializer(ModelSerializer):

    def to_representation(self, data):
        # If the content object was deleted
        if data.content_object is None:
            return None
        try:
            if not data.content_object.complete:
                return None
        except AttributeError:
            pass
        request = self.context['request']
        viewset = viewset_for_model(data.content_object)
        serializer = viewset.serializer_class(data.content_object, context={'request': request})
        return serializer.data.get('_href')

    class Meta:
        model = models.CreatedResource
        fields = ModelSerializer.Meta.fields


class TaskSerializer(MasterModelSerializer):
    _href = DetailIdentityField()

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
        view_name='workers-detail'
    )

    parent = serializers.HyperlinkedRelatedField(
        help_text=_("The parent task that spawned this task."),
        read_only=True,
        view_name='tasks-detail'
    )

    spawned_tasks = serializers.HyperlinkedRelatedField(
        help_text=_("Any tasks spawned by this task."),
        many=True,
        read_only=True,
        view_name='tasks-detail'
    )

    progress_reports = ProgressReportSerializer(
        many=True,
        read_only=True
    )

    created_resources = CreatedResourceSerializer(
        help_text=_('Resources created by this task.'),
        many=True,
        read_only=True
    )

    def create(self, validated_data):

        self.task = super().create(validated_data)
        self.celery_task.apply_async_with_reservation(
            self.task_args,
            task_status=self.task,
            kwargs=self.task_kwargs
        )
        return self.task

    @property
    def task_args(self):
        task_args = []
        for string_value in self.task_arg_structure:
            task_args.append(self._str_to_nested_value(string_value))
        return task_args

    @property
    def task_kwargs(self):
        task_kwargs = {}
        for (key, value) in self.task_kwarg_structure.items():
            task_kwargs[key] = self._str_to_nested_value(value)
        return task_kwargs

    def _str_to_nested_value(self, nested_string):
        nested_layers = nested_string.split('.')
        value = self.task
        for layer in nested_layers:
            value = getattr(value, layer)

        return value

    class Meta:
        model = models.Task
        # Fields that serialize tasks are broken in this WIP
        fields = ModelSerializer.Meta.fields + ('state', 'started_at', 'finished_at',
                                                'non_fatal_errors', 'error', 'worker',
                                                # 'parent',
                                                # 'spawned_tasks',
                                                # 'progress_reports',
                                                'created_resources')


class CoreUpdateTaskSerializer(TaskSerializer):

    class Meta:
        model = CoreUpdateTask
        fields = TaskSerializer.Meta.fields


class WorkerSerializer(ModelSerializer):
    _href = serializers.HyperlinkedIdentityField(view_name='workers-detail')

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
