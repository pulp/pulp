from gettext import gettext as _

from django.core import validators
from django.db.models import Q

from rest_framework import serializers, fields
from rest_framework.validators import UniqueValidator

from pulpcore.app import models
from pulpcore.app.serializers import (
    BaseURLField,
    DetailIdentityField,
    DetailRelatedField,
    GenericKeyValueRelatedField,
    IdentityField,
    NestedIdentityField,
    NestedRelatedField,
    RelatedField,
    LatestVersionField,
    MasterModelSerializer,
    ModelSerializer,
)
from pulpcore.app.serializers import validate_unknown_fields
from rest_framework_nested.serializers import NestedHyperlinkedModelSerializer


class RepositorySerializer(ModelSerializer):
    _href = IdentityField(
        view_name='repositories-detail'
    )
    _versions_href = IdentityField(
        view_name='versions-list',
        lookup_url_kwarg='repository_pk',
    )
    _latest_version_href = LatestVersionField()
    name = serializers.CharField(
        help_text=_('A unique name for this repository.'),
        validators=[UniqueValidator(queryset=models.Repository.objects.all())]
    )
    description = serializers.CharField(
        help_text=_('An optional description.'),
        required=False,
        allow_blank=True
    )
    notes = GenericKeyValueRelatedField(
        help_text=_('A mapping of string keys to string values, for storing notes on this object.'),
        required=False
    )

    class Meta:
        model = models.Repository
        fields = ModelSerializer.Meta.fields + ('_versions_href', '_latest_version_href', 'name',
                                                'description', 'notes')


class RemoteSerializer(MasterModelSerializer):
    """
    Every remote defined by a plugin should have a Remote serializer that inherits from this
    class. Please import from `pulpcore.plugin.serializers` rather than from this module directly.
    """
    _href = DetailIdentityField()
    name = serializers.CharField(
        help_text=_('A unique name for this remote.'),
        validators=[UniqueValidator(queryset=models.Remote.objects.all())],
    )
    url = serializers.CharField(
        help_text='The URL of an external content source.',
    )
    validate = serializers.BooleanField(
        help_text='If True, the plugin will validate imported artifacts.',
        required=False,
    )
    ssl_ca_certificate = serializers.FileField(
        help_text='A PEM encoded CA certificate used to validate the server '
                  'certificate presented by the remote server.',
        write_only=True,
        required=False,
    )
    ssl_client_certificate = serializers.FileField(
        help_text='A PEM encoded client certificate used for authentication.',
        write_only=True,
        required=False,
    )
    ssl_client_key = serializers.FileField(
        help_text='A PEM encoded private key used for authentication.',
        write_only=True,
        required=False,
    )
    ssl_validation = serializers.BooleanField(
        help_text='If True, SSL peer validation must be performed.',
        required=False,
    )
    proxy_url = serializers.CharField(
        help_text='The proxy URL. Format: scheme://user:password@host:port',
        required=False,
        allow_blank=True,
    )
    username = serializers.CharField(
        help_text='The username to be used for authentication when syncing.',
        write_only=True,
        required=False,
        allow_blank=True,
    )
    password = serializers.CharField(
        help_text='The password to be used for authentication when syncing.',
        write_only=True,
        required=False,
        allow_blank=True,
    )
    last_synced = serializers.DateTimeField(
        help_text='Timestamp of the most recent successful sync.',
        read_only=True
    )
    last_updated = serializers.DateTimeField(
        help_text='Timestamp of the most recent update of the remote.',
        read_only=True
    )
    connection_limit = serializers.IntegerField(
        help_text='Total number of simultaneous connections.',
        required=False,
        min_value=1
    )

    class Meta:
        abstract = True
        model = models.Remote
        fields = MasterModelSerializer.Meta.fields + (
            'name', 'url', 'validate', 'ssl_ca_certificate', 'ssl_client_certificate',
            'ssl_client_key', 'ssl_validation', 'proxy_url', 'username', 'password', 'last_synced',
            'last_updated', 'connection_limit')


class RepositorySyncURLSerializer(serializers.Serializer):
    repository = serializers.HyperlinkedRelatedField(
        required=True,
        help_text=_('A URI of the repository to be synchronized.'),
        queryset=models.Repository.objects.all(),
        view_name='repositories-detail',
        label=_('Repository'),
        error_messages={
            'required': _('The repository URI must be specified.')
        }
    )

    mirror = fields.BooleanField(
        required=False,
        default=True,
        help_text=_('The synchronization mode, True for "mirror" and False for "additive" mode.')
    )


class PublisherSerializer(MasterModelSerializer):
    """
    Every publisher defined by a plugin should have an Publisher serializer that inherits from this
    class. Please import from `pulpcore.plugin.serializers` rather than from this module directly.
    """
    _href = DetailIdentityField()
    name = serializers.CharField(
        help_text=_('A unique name for this publisher.'),
        validators=[UniqueValidator(queryset=models.Publisher.objects.all())]
    )
    last_updated = serializers.DateTimeField(
        help_text=_('Timestamp of the most recent update of the publisher configuration.'),
        read_only=True
    )
    last_published = serializers.DateTimeField(
        help_text=_('Timestamp of the most recent successful publish.'),
        read_only=True
    )
    distributions = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='distributions-detail',
    )

    class Meta:
        abstract = True
        model = models.Publisher
        fields = MasterModelSerializer.Meta.fields + (
            'name', 'last_updated', 'last_published', 'distributions',
        )


class RepositoryPublishURLSerializer(serializers.Serializer):

    repository = serializers.HyperlinkedRelatedField(
        help_text=_('A URI of the repository to be synchronized.'),
        required=False,
        label=_('Repository'),
        queryset=models.Repository.objects.all(),
        view_name='repositories-detail',
    )

    repository_version = NestedRelatedField(
        help_text=_('A URI of the repository version to be published.'),
        required=False,
        label=_('Repository Version'),
        queryset=models.RepositoryVersion.objects.all(),
        view_name='versions-detail',
        lookup_field='number',
        parent_lookup_kwargs={'repository_pk': 'repository__pk'},
    )

    def validate(self, data):
        if hasattr(self, 'initial_data'):
            validate_unknown_fields(self.initial_data, self.fields)

        repository = data.pop('repository', None)
        repository_version = data.get('repository_version')
        if not repository and not repository_version:
            raise serializers.ValidationError(
                _("Either the 'repository' or 'repository_version' need to be specified"))
        elif not repository and repository_version:
            return data
        elif repository and not repository_version:
            version = models.RepositoryVersion.latest(repository)
            if version:
                new_data = {'repository_version': version}
                new_data.update(data)
                return new_data
            else:
                raise serializers.ValidationError(
                    detail=_('Repository has no version available to publish'))
        raise serializers.ValidationError(
            _("Either the 'repository' or 'repository_version' need to be specified "
              "but not both.")
        )


class ExporterSerializer(MasterModelSerializer):
    _href = DetailIdentityField()
    name = serializers.CharField(
        help_text=_('The exporter unique name.'),
        validators=[UniqueValidator(queryset=models.Exporter.objects.all())]
    )
    last_updated = serializers.DateTimeField(
        help_text=_('Timestamp of the last update.'),
        read_only=True
    )
    last_export = serializers.DateTimeField(
        help_text=_('Timestamp of the last export.'),
        read_only=True
    )

    class Meta:
        abstract = True
        model = models.Exporter
        fields = MasterModelSerializer.Meta.fields + (
            'name',
            'last_updated',
            'last_export',
        )


class DistributionSerializer(ModelSerializer):
    _href = IdentityField(
        view_name='distributions-detail'
    )
    name = serializers.CharField(
        help_text=_('A unique distribution name. Ex, `rawhide` and `stable`.'),
        validators=[validators.MaxLengthValidator(
            models.Distribution._meta.get_field('name').max_length,
            message=_('Distribution name length must be less than {} characters').format(
                models.Distribution._meta.get_field('name').max_length
            )),
            UniqueValidator(queryset=models.Distribution.objects.all())]
    )
    base_path = serializers.CharField(
        help_text=_('The base (relative) path component of the published url. Avoid paths that \
                    overlap with other distribution base paths (e.g. "foo" and "foo/bar")'),
        validators=[validators.MaxLengthValidator(
            models.Distribution._meta.get_field('base_path').max_length,
            message=_('Distribution base_path length must be less than {} characters').format(
                models.Distribution._meta.get_field('base_path').max_length
            )),
            UniqueValidator(queryset=models.Distribution.objects.all()),
        ]
    )
    publisher = DetailRelatedField(
        required=False,
        help_text=_('Publications created by this publisher and repository are automatically'
                    'served as defined by this distribution'),
        queryset=models.Publisher.objects.all(),
        allow_null=True
    )
    content_guard = DetailRelatedField(
        required=False,
        help_text=_('An optional content-guard.'),
        queryset=models.ContentGuard.objects.all(),
        allow_null=True
    )
    publication = RelatedField(
        required=False,
        help_text=_('The publication being served as defined by this distribution'),
        queryset=models.Publication.objects.exclude(complete=False),
        view_name='publications-detail',
        allow_null=True
    )
    repository = serializers.HyperlinkedRelatedField(
        required=False,
        help_text=_('Publications created by this repository and publisher are automatically'
                    'served as defined by this distribution'),
        queryset=models.Repository.objects.all(),
        view_name='repositories-detail',
        allow_null=True
    )
    base_url = BaseURLField(
        source='base_path', read_only=True,
        help_text=_('The URL for accessing the publication as defined by this distribution.')
    )

    class Meta:
        model = models.Distribution
        fields = ModelSerializer.Meta.fields + (
            'name',
            'base_path',
            'publisher',
            'publication',
            'base_url',
            'repository',
            'content_guard',
        )

    def _validate_path_overlap(self, path):
        # look for any base paths nested in path
        search = path.split("/")[0]
        q = Q(base_path=search)
        for subdir in path.split("/")[1:]:
            search = "/".join((search, subdir))
            q |= Q(base_path=search)

        # look for any base paths that nest path
        q |= Q(base_path__startswith='{}/'.format(path))
        qs = models.Distribution.objects.filter(q)

        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)

        match = qs.first()
        if match:
            raise serializers.ValidationError(detail=_("Overlaps with existing distribution '"
                                                       "{}'").format(match.name))

        return path

    def validate_base_path(self, path):
        self._validate_relative_path(path)
        return self._validate_path_overlap(path)

    def validate(self, data):
        super().validate(data)

        if 'publisher' in data:
            publisher = data['publisher']
        elif self.instance:
            publisher = self.instance.publisher
        else:
            publisher = None

        if 'repository' in data:
            repository = data['repository']
        elif self.instance:
            repository = self.instance.repository
        else:
            repository = None

        if publisher and not repository:
            raise serializers.ValidationError({'repository': _("Repository must be set if "
                                                               "publisher is set.")})
        if repository and not publisher:
            raise serializers.ValidationError({'publisher': _("Publisher must be set if "
                                                              "repository is set.")})

        return data


class PublicationSerializer(ModelSerializer):
    _href = IdentityField(
        view_name='publications-detail'
    )
    pass_through = serializers.BooleanField(
        help_text=_('The publication is a pass-through for the repository version.')
    )
    publisher = DetailRelatedField(
        help_text=_('The publisher that created this publication.'),
        queryset=models.Publisher.objects.all()
    )
    distributions = serializers.HyperlinkedRelatedField(
        help_text=_('This publication is currently being served as'
                    'defined by these distributions.'),
        many=True,
        read_only=True,
        view_name='distributions-detail',
    )
    repository_version = NestedRelatedField(
        view_name='versions-detail',
        lookup_field='number',
        parent_lookup_kwargs={'repository_pk': 'repository__pk'},
        read_only=True,
    )

    class Meta:
        model = models.Publication
        fields = ModelSerializer.Meta.fields + (
            'pass_through',
            'publisher',
            'distributions',
            'repository_version',
        )


class RepositoryVersionSerializer(ModelSerializer, NestedHyperlinkedModelSerializer):
    _href = NestedIdentityField(
        view_name='versions-detail',
        lookup_field='number', parent_lookup_kwargs={'repository_pk': 'repository__pk'},
    )
    _content_href = NestedIdentityField(
        view_name='versions-content',
        lookup_field='number', parent_lookup_kwargs={'repository_pk': 'repository__pk'},
    )
    _added_href = NestedIdentityField(
        view_name='versions-added-content',
        lookup_field='number', parent_lookup_kwargs={'repository_pk': 'repository__pk'},
    )
    _removed_href = NestedIdentityField(
        view_name='versions-removed-content',
        lookup_field='number', parent_lookup_kwargs={'repository_pk': 'repository__pk'},
    )
    number = serializers.IntegerField(
        read_only=True
    )
    content_summary = serializers.DictField(
        help_text=_('A list of counts of each type of content in this version.'),
        read_only=True
    )
    base_version = NestedRelatedField(
        required=False,
        help_text=_('A repository version whose content was used as the initial set of content '
                    'for this repository version'),
        queryset=models.RepositoryVersion.objects.all(),
        view_name='versions-detail',
        lookup_field='number',
        parent_lookup_kwargs={'repository_pk': 'repository__pk'},
    )

    class Meta:
        model = models.RepositoryVersion
        fields = ModelSerializer.Meta.fields + (
            '_href', '_content_href', '_added_href', '_removed_href', 'number',
            'content_summary', 'base_version'
        )


class RepositoryVersionCreateSerializer(ModelSerializer, NestedHyperlinkedModelSerializer):
    add_content_units = serializers.ListField(
        help_text=_('A list of content units to add to a new repository version'),
        write_only=True
    )
    remove_content_units = serializers.ListField(
        help_text=_('A list of content units to remove from the latest repository version'),
        write_only=True
    )
    base_version = NestedRelatedField(
        required=False,
        help_text=_('A repository version whose content will be used as the initial set of content '
                    'for the new repository version'),
        queryset=models.RepositoryVersion.objects.all(),
        view_name='versions-detail',
        lookup_field='number',
        parent_lookup_kwargs={'repository_pk': 'repository__pk'},
    )

    class Meta:
        model = models.RepositoryVersion
        fields = ['add_content_units', 'remove_content_units', 'base_version']
