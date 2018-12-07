from gettext import gettext as _

from rest_framework import serializers

from pulpcore.app import models
from pulpcore.app.serializers import ModelSerializer, RelatedField


class ProgressReportSerializer(ModelSerializer):

    message = serializers.CharField(
        help_text=_("The message shown to the user for the progress report."),
        read_only=True
    )
    state = serializers.CharField(
        help_text=_("The current state of the progress report. The possible values are:"
                    " 'waiting', 'skipped', 'running', 'completed', 'failed' and 'canceled'."
                    " The default is 'waiting'."),
        read_only=True
    )
    total = serializers.IntegerField(
        help_text=_("The total count of items to be handled by the ProgressBar."),
        read_only=True
    )
    done = serializers.IntegerField(
        help_text=_("The count of items already processed. Defaults to 0."),
        read_only=True
    )
    suffix = serializers.CharField(
        help_text=_("The suffix to be shown with the progress report."),
        read_only=True,
        allow_blank=True
    )
    task = RelatedField(
        help_text=_("The task associated with this progress report."),
        read_only=True,
        view_name='tasks-detail'
    )

    class Meta:
        model = models.ProgressReport
        # this serializer is meant to be nested inside Task serializer,
        # so it will not have its own endpoint, that's why
        # we need to explicitly define fields to exclude '_href' field.
        fields = ('message', 'state', 'total', 'done', 'suffix', 'task')
