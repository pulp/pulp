from rest_framework import serializers

from pulp.app import models
from pulp.app.serializers import NotesKeyValueRelatedField, ModelSerializer


class RepositorySerializer(ModelSerializer):
    # _href is normally provided by the base class, but Repository's
    # "name" lookup field means _href must be explicitly declared.
    _href = serializers.HyperlinkedIdentityField(
        view_name='repository-detail',
        lookup_field='name',
    )
    name = serializers.CharField(
        help_text='A unique name for this repository.',
        write_only=True
    )

    description = serializers.CharField(
        help_text='An optional description.',
        required=False
    )

    last_content_added = serializers.DateTimeField(
        help_text='Timestamp of the most recent addition of content to this repository.',
        read_only=True
    )

    last_content_removed = serializers.DateTimeField(
        help_text='Timestamp of the most recent removal of content to this repository.',
        read_only=True
    )
    notes = NotesKeyValueRelatedField()

    class Meta:
        model = models.Repository
        fields = ModelSerializer.Meta.fields + ('name', 'description', 'notes',
                                                'last_content_added', 'last_content_removed')

