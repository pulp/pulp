from gettext import gettext as _

from django.core import validators

from rest_framework import serializers
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator

from pulpcore.app import models
from pulpcore.app.serializers import (
    ContentRelatedField,
    DetailIdentityField,
    DetailRelatedField,
    FileField,
    GenericKeyValueRelatedField,
    MasterModelSerializer,
    ModelSerializer,
)


class RepositorySerializer(ModelSerializer):
    _href = serializers.HyperlinkedIdentityField(
        view_name='repositories-detail'
    )
    name = serializers.CharField(
        help_text=_('A unique name for this repository.'),
        validators=[UniqueValidator(queryset=models.Repository.objects.all())]
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
    notes = GenericKeyValueRelatedField(
        help_text=_('A mapping of string keys to string values, for storing notes on this object.'),
        required=False
    )
    importers = DetailRelatedField(many=True, read_only=True, lookup_field='name')
    publishers = DetailRelatedField(many=True, read_only=True, lookup_field='name')
    content = serializers.HyperlinkedIdentityField(
        view_name='repositories-content',
    )

    content_summary = serializers.DictField(
        help_text=_('A list of counts of each type of content in this repository.'),
        read_only=True
    )

    class Meta:
        model = models.Repository
        fields = ModelSerializer.Meta.fields + ('name', 'description', 'notes',
                                                'last_content_added', 'last_content_removed',
                                                'importers', 'publishers', 'content',
                                                'content_summary')


class ImporterSerializer(MasterModelSerializer):
    """
    Every importer defined by a plugin should have an Importer serializer that inherits from this
    class. Please import from `pulpcore.plugin.serializers` rather than from this module directly.
    """
    _href = DetailIdentityField(lookup_field='name')
    name = serializers.CharField(
        help_text=_('A name for this importer, unique within the associated repository.')
    )
    feed_url = serializers.CharField(
        help_text='The URL of an external content source.',
        required=False,
    )
    download_policy = serializers.ChoiceField(
        help_text='The policy for downloading content.',
        allow_blank=False,
        choices=models.Importer.DOWNLOAD_POLICIES,
    )
    sync_mode = serializers.ChoiceField(
        help_text='How the importer should sync from the upstream repository.',
        allow_blank=False,
        choices=models.Importer.SYNC_MODES,
    )
    validate = serializers.BooleanField(
        help_text='If True, the plugin will validate imported artifacts.',
        required=False,
    )
    ssl_ca_certificate = FileField(
        help_text='A PEM encoded CA certificate used to validate the server '
                  'certificate presented by the remote server.',
        write_only=True,
        required=False,
    )
    ssl_client_certificate = FileField(
        help_text='A PEM encoded client certificate used for authentication.',
        write_only=True,
        required=False,
    )
    ssl_client_key = FileField(
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
    )
    username = serializers.CharField(
        help_text='The username to be used for authentication when syncing.',
        write_only=True,
        required=False,
    )
    password = serializers.CharField(
        help_text='The password to be used for authentication when syncing.',
        write_only=True,
        required=False,
    )
    last_synced = serializers.DateTimeField(
        help_text='Timestamp of the most recent successful sync.',
        read_only=True
    )
    last_updated = serializers.DateTimeField(
        help_text='Timestamp of the most recent update of the importer.',
        read_only=True
    )

    repository = serializers.HyperlinkedRelatedField(
        view_name='repositories-detail',
        queryset=models.Repository.objects.all(),
    )

    class Meta:
        abstract = True
        model = models.Importer
        fields = MasterModelSerializer.Meta.fields + (
            'name', 'feed_url', 'download_policy', 'sync_mode', 'validate', 'ssl_ca_certificate',
            'ssl_client_certificate', 'ssl_client_key', 'ssl_validation', 'proxy_url',
            'username', 'password', 'last_synced', 'last_updated', 'repository',
        )
        validators = [
            UniqueTogetherValidator(
                queryset=models.Importer.objects.all(),
                fields=('name', 'repository')
            )
        ]


class PublisherSerializer(MasterModelSerializer):
    """
    Every publisher defined by a plugin should have an Publisher serializer that inherits from this
    class. Please import from `pulpcore.plugin.serializers` rather than from this module directly.
    """
    _href = DetailIdentityField(lookup_field='name')
    name = serializers.CharField(
        help_text=_('A name for this publisher, unique within the associated repository.')
    )
    last_updated = serializers.DateTimeField(
        help_text=_('Timestamp of the most recent update of the publisher configuration.'),
        read_only=True
    )
    repository = serializers.HyperlinkedRelatedField(
        view_name='repositories-detail',
        queryset=models.Repository.objects.all(),
    )
    auto_publish = serializers.BooleanField(
        help_text=_('An indication that the automatic publish may happen when'
                    ' the repository content has changed.'),
        required=False
    )
    last_published = serializers.DateTimeField(
        help_text=_('Timestamp of the most recent successful publish.'),
        read_only=True
    )
    distributions = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        lookup_field='name',
        view_name='distributions-detail',
    )

    class Meta:
        abstract = True
        model = models.Publisher
        fields = MasterModelSerializer.Meta.fields + (
            'name', 'last_updated', 'repository', 'auto_publish', 'last_published', 'distributions',
        )
        validators = [
            UniqueTogetherValidator(
                queryset=models.Publisher.objects.all(),
                fields=('name', 'repository')
            )
        ]


class DistributionSerializer(ModelSerializer):
    _href = serializers.HyperlinkedIdentityField(
        lookup_field='name',
        view_name='distributions-detail'
    )
    name = serializers.CharField(
        help_text=_('The name of the distribution. Ex, `rawhide` and `stable`.'),
        validators=[validators.MaxLengthValidator(
            models.Distribution._meta.get_field('name').max_length,
            message=_('Distribution name length must be less than {} characters').format(
                models.Distribution._meta.get_field('name').max_length
            ))]
    )
    base_path = serializers.CharField(
        help_text=('The base (relative) path component of the published url.'),
        validators=[validators.MaxLengthValidator(
            models.Distribution._meta.get_field('base_path').max_length,
            message=_('Distribution base_path length must be less than {} characters').format(
                models.Distribution._meta.get_field('base_path').max_length
            )),
            UniqueValidator(queryset=models.Distribution.objects.all()),
        ],
    )
    auto_updated = serializers.BooleanField(
        help_text=_('The publication is updated automatically when the publisher has created a '
                    'new publication'),
    )
    http = serializers.BooleanField(
        help_text=('The publication is distributed using HTTP.'),
    )
    https = serializers.BooleanField(
        help_text=_('The publication is distributed using HTTPS.')
    )
    publisher = DetailRelatedField(
        queryset=models.Publisher.objects.all(),
        lookup_field='name',
    )

    class Meta:
        model = models.Distribution
        fields = ModelSerializer.Meta.fields + (
            'name', 'base_path', 'auto_updated', 'http', 'https', 'publisher',
        )


class RepositoryContentSerializer(ModelSerializer):
    _href = serializers.HyperlinkedIdentityField(
        view_name='repositorycontents-detail'
    )

    content = ContentRelatedField()
    repository = serializers.HyperlinkedRelatedField(
        view_name='repositories-detail',
        queryset=models.Repository.objects.all()
    )

    class Meta:
        model = models.RepositoryContent
        fields = ('_href', 'repository', 'content')
