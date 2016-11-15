from gettext import gettext as _

from rest_framework import serializers

from pulp.app import models
from pulp.app.serializers import (MasterModelSerializer, ModelSerializer,
                                  NotesKeyValueRelatedField, RepositoryRelatedField,
                                  ScratchpadKeyValueRelatedField)


class RepositorySerializer(ModelSerializer):
    # _href is normally provided by the base class, but Repository's
    # "name" lookup field means _href must be explicitly declared.
    _href = serializers.HyperlinkedIdentityField(
        view_name='repositories-detail',
        lookup_field='name',
    )
    name = serializers.CharField(
        help_text=_('A unique name for this repository.'),
        write_only=True
    )

    description = serializers.CharField(
        help_text=_('An optional description.'),
        required=False
    )

    last_content_added = serializers.DateTimeField(
        help_text=_('Timestamp of the most recent addition of content to this repository.'),
        read_only=True
    )

    last_content_removed = serializers.DateTimeField(
        help_text=_('Timestamp of the most recent removal of content to this repository.'),
        read_only=True
    )
    notes = NotesKeyValueRelatedField()
    scratchpad = ScratchpadKeyValueRelatedField()

    class Meta:
        model = models.Repository
        fields = ModelSerializer.Meta.fields + ('name', 'description', 'notes', 'scratchpad',
                                                'last_content_added', 'last_content_removed')


class RepositoryGroupSerializer(ModelSerializer):

    _href = serializers.HyperlinkedIdentityField(
        view_name='repo_groups-detail',
        lookup_field='name',
    )

    name = serializers.CharField(
        help_text=_('A unique name for this repository group.')
    )
    description = serializers.CharField(
        help_text=_('An optional description of the repository group.'),
        required=False
    )
    members = RepositoryRelatedField(many=True)
    scratchpad = ScratchpadKeyValueRelatedField()
    notes = NotesKeyValueRelatedField()

    class Meta:
        model = models.RepositoryGroup
        fields = ModelSerializer.Meta.fields + ('name', 'description', 'members', 'scratchpad',
                                                'notes')


class ImporterSerializer(MasterModelSerializer):
    """
    Every importer defined by a plugin should have an Importer serializer that inherits from this
    class. Please import from `pulp.app.serializers` rather than from this module directly.

    Every subclass must override the `_href` field with a `RepositoryNestedIdentityField` that
    defines the view_name.
    """
    name = serializers.CharField(
        help_text=_('A name for this importer, unique within the associated repository.')
    )

    class Meta:
        abstract = True
        fields = MasterModelSerializer.Meta.fields + ('name',)


class PublisherSerializer(MasterModelSerializer):
    """
    Every publisher defined by a plugin should have an Publisher serializer that inherits from this
    class. Please import from `pulp.app.serializers` rather than from this module directly.
    """
    # Every subclass must override the `_href` field with a `RepositoryNestedIdentityField` that
    # defines the view_name.
    _href = serializers.HyperlinkedIdentityField(
        view_name='publishers-detail',
        lookup_field='name',
    )
    name = serializers.CharField(
        help_text=_('A name for this publisher, unique within the associated repository.')
    )
    last_updated = serializers.DateTimeField(
        help_text=_('Timestamp of the most recent update of the publisher configuration.'),
        read_only=True
    )
    repository = RepositoryRelatedField()

    auto_publish = serializers.BooleanField(
        help_text=_('An indicaton that the automatic publish may happen when'
                    ' the repository content has changed.'),
        required=False
    )
    relative_path = serializers.CharField(
        help_text=_('The (relative) path component of the published url'),
        required=False
    )
    last_published = serializers.DateTimeField(
        help_text=_('Timestamp of the most recent successful publish.'),
        read_only=True
    )

    class Meta:
        abstract = True
        model = models.Publisher
        fields = MasterModelSerializer.Meta.fields + (
            'name', 'last_updated', 'repository', 'auto_publish', 'relative_path', 'last_published'
        )
