from gettext import gettext as _

from rest_framework import serializers
from rest_framework_nested.serializers import NestedHyperlinkedModelSerializer

from pulpcore.app import models
from pulpcore.app.serializers import (MasterModelSerializer, ModelSerializer,
                                      HrefWritableRepositoryRelatedField,
                                      GenericKeyValueRelatedField,
                                      DetailWritableNestedUrlRelatedField,
                                      ContentRelatedField,
                                      FileField,
                                      DetailNestedHyperlinkedRelatedField,
                                      DetailNestedHyperlinkedIdentityField)

from rest_framework_nested.relations import (NestedHyperlinkedRelatedField,
                                             NestedHyperlinkedIdentityField)


class RepositorySerializer(ModelSerializer):
    # _href is normally provided by the base class, but Repository's
    # "name" lookup field means _href must be explicitly declared.
    _href = serializers.HyperlinkedIdentityField(
        view_name='repositories-detail',
        lookup_field='name',
    )
    name = serializers.CharField(
        help_text=_('A unique name for this repository.')
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
    importers = DetailNestedHyperlinkedRelatedField(many=True, read_only=True,
                                                    parent_lookup_kwargs={'repository_name':
                                                                          'repository__name'},
                                                    lookup_field='name')
    publishers = DetailNestedHyperlinkedRelatedField(many=True, read_only=True,
                                                     parent_lookup_kwargs={'repository_name':
                                                                           'repository__name'},
                                                     lookup_field='name')
    content = serializers.HyperlinkedIdentityField(
        view_name='repositories-content',
        lookup_field='name'
    )

    class Meta:
        model = models.Repository
        fields = ModelSerializer.Meta.fields + ('name', 'description', 'notes',
                                                'last_content_added', 'last_content_removed',
                                                'importers', 'publishers', 'content')


class ImporterSerializer(MasterModelSerializer, NestedHyperlinkedModelSerializer):
    """
    Every importer defined by a plugin should have an Importer serializer that inherits from this
    class. Please import from `pulpcore.plugin.serializers` rather than from this module directly.
    """
    _href = DetailNestedHyperlinkedIdentityField(
        lookup_field='name', parent_lookup_kwargs={'repository_name': 'repository__name'},
    )
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

    repository = HrefWritableRepositoryRelatedField(read_only=True)

    class Meta:
        abstract = True
        model = models.Importer
        fields = MasterModelSerializer.Meta.fields + (
            'name', 'feed_url', 'download_policy', 'sync_mode', 'validate', 'ssl_ca_certificate',
            'ssl_client_certificate', 'ssl_client_key', 'ssl_validation', 'proxy_url',
            'username', 'password', 'last_synced', 'last_updated', 'repository',
        )


class PublisherSerializer(MasterModelSerializer, NestedHyperlinkedModelSerializer):
    """
    Every publisher defined by a plugin should have an Publisher serializer that inherits from this
    class. Please import from `pulpcore.plugin.serializers` rather than from this module directly.
    """
    _href = DetailNestedHyperlinkedIdentityField(
        lookup_field='name', parent_lookup_kwargs={'repository_name': 'repository__name'},
    )
    name = serializers.CharField(
        help_text=_('A name for this publisher, unique within the associated repository.')
    )
    last_updated = serializers.DateTimeField(
        help_text=_('Timestamp of the most recent update of the publisher configuration.'),
        read_only=True
    )
    repository = HrefWritableRepositoryRelatedField(read_only=True)

    auto_publish = serializers.BooleanField(
        help_text=_('An indicaton that the automatic publish may happen when'
                    ' the repository content has changed.'),
        required=False
    )
    last_published = serializers.DateTimeField(
        help_text=_('Timestamp of the most recent successful publish.'),
        read_only=True
    )
    distributions = NestedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        parent_lookup_kwargs={'publisher_name': 'publisher__name',
                              'repository_name': 'publisher__repository__name'},
        view_name='distributions-detail',
        lookup_field='name'
    )

    class Meta:
        abstract = True
        model = models.Publisher
        fields = MasterModelSerializer.Meta.fields + (
            'name', 'last_updated', 'repository', 'auto_publish', 'last_published', 'distributions',
        )


class DistributionSerializer(ModelSerializer):
    _href = NestedHyperlinkedIdentityField(
        lookup_field='name',
        parent_lookup_kwargs={'repository_name': 'publisher__repository__name',
                              'publisher_name': 'publisher__name'},
        view_name='distributions-detail'
    )
    name = serializers.CharField(
        help_text=_('The name of the distribution. Ex, `rawhide` and `stable`.'),
    )
    base_path = serializers.CharField(
        help_text=('The base (relative) path component of the published url.'),
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
    publisher = DetailWritableNestedUrlRelatedField(
        parent_lookup_kwargs={'repository_name': 'repository__name'},
        lookup_field='name',
        read_only=True
    )

    class Meta:
        model = models.Distribution
        fields = ModelSerializer.Meta.fields + (
            'name', 'base_path', 'auto_updated', 'http', 'https', 'publisher',
        )


class RepositoryContentSerializer(serializers.ModelSerializer):
    # RepositoryContentSerizlizer should not have it's own _href, so it subclasses
    # rest_framework.serializers.ModelSerializer instead of pulpcore.app.serializers.ModelSerializer
    content = ContentRelatedField()
    repository = serializers.HyperlinkedRelatedField(
        view_name='repositories-detail',
        lookup_field='name',
        queryset=models.Repository.objects.all()
    )

    class Meta:
        model = models.RepositoryContent
        fields = ('repository', 'content')
