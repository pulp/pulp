from collections import OrderedDict
from gettext import gettext as _

from rest_framework import serializers

from pulpcore.app import models
from pulpcore.app.serializers import IdentifierField, ModelSerializer, ProgressReportSerializer

from .base import viewset_for_model


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

        created_resource = {
            '_href': serializer.data.get('_href'),
            'pk': serializer.data.get('id')
        }
        if 'number' in serializer.data:
            created_resource['number'] = serializer.data.get('number')
        return created_resource

    class Meta:
        model = models.CreatedResource
        fields = ModelSerializer.Meta.fields

        swagger_schema_fields = {
            'properties': OrderedDict([
                ('pk', OrderedDict([
                    ('title', 'PK'),
                    ('type', 'integer'),
                    ('readOnly', 'true'),
                ])),
                ('_href', OrderedDict([
                    ('title', 'href'),
                    ('type', 'string'),
                    ('format', 'uri'),
                    ('readOnly', 'true'),
                ])),
                ('created', OrderedDict([
                    ('title', 'Created'),
                    ('description', 'Timestamp of creation.'),
                    ('type', 'string'),
                    ('format', 'date-time'),
                    ('readOnly', 'true'),
                ]))
            ]),
            'additional_properties': True
        }


class TaskSerializer(ModelSerializer):
    _href = serializers.HyperlinkedIdentityField(
        view_name='tasks-detail',
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
    worker = IdentifierField(
        help_text=_("The worker associated with this task."
                    " This field is empty if a worker is not yet assigned."),
        read_only=True,
        view_name='workers-detail'
    )
    parent = IdentifierField(
        help_text=_("The parent task that spawned this task."),
        read_only=True,
        view_name='tasks-detail'
    )
    spawned_tasks = IdentifierField(
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

    class Meta:
        model = models.Task
        fields = ModelSerializer.Meta.fields + ('state', 'started_at', 'finished_at',
                                                'non_fatal_errors', 'error', 'worker', 'parent',
                                                'spawned_tasks', 'progress_reports',
                                                'created_resources')


class MinimalTaskSerializer(TaskSerializer):

    class Meta:
        model = models.Task
        fields = ModelSerializer.Meta.fields + ('state', 'started_at', 'finished_at',
                                                'worker', 'parent')


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
        help_text=_('True if the worker is considered online, otherwise False'),
        read_only=True
    )
    missing = serializers.BooleanField(
        help_text=_('True if the worker is considerd missing, otherwise False'),
        read_only=True
    )
    # disable "created" because we don't care about it
    created = None

    class Meta:
        model = models.Worker
        _base_fields = tuple(set(ModelSerializer.Meta.fields) - set(['created']))
        fields = _base_fields + ('name', 'last_heartbeat', 'online', 'missing')
