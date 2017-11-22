"""
Repository related Django models.
"""
from contextlib import suppress

from django.db import models
from django.db.utils import IntegrityError

from pulpcore.app.models import Model, Notes, MasterModel, GenericKeyValueRelation
from pulpcore.app.models.storage import get_tls_path


class Repository(Model):
    """
    Collection of content.

    Fields:

        name (models.TextField): The repository name.
        description (models.TextField): An optional description.

    Relations:

        notes (GenericKeyValueRelation): Arbitrary repository properties.
        content (models.ManyToManyField): Associated content.
    """
    name = models.TextField(db_index=True, unique=True)
    description = models.TextField(blank=True)

    notes = GenericKeyValueRelation(Notes)

    content = models.ManyToManyField('Content', through='RepositoryContent',
                                     related_name='repositories')

    class Meta:
        verbose_name_plural = 'repositories'

    def natural_key(self):
        """
        Get the model's natural key.

        :return: The model's natural key.
        :rtype: tuple
        """
        return (self.name,)


class ContentAdaptor(MasterModel):
    """
    An Abstract model for objects that import or publish content.

    Fields:

        name (models.TextField): The ContentAdaptor name.
        last_updated (models.DatetimeField): When the adaptor was last updated.

    Relations:

        repository (models.ForeignKey): The associated repository.
    """
    name = models.TextField(db_index=True)
    last_updated = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        abstract = True
        unique_together = ('repository', 'name')

    def natural_key(self):
        """
        Get the model's natural key.

        Returns:

            tuple: The model's natural key.
        """
        return (self.repository, self.name)


class Importer(ContentAdaptor):
    """
    A content importer.

    Fields:

        feed_url (models.TextField): The URL of an external content source.
        validate (models.BooleanField): If True, the plugin will validate imported files.
        ssl_ca_certificate (models.TextField): A PEM encoded CA certificate used to validate the
            server certificate presented by the external source.
        ssl_client_certificate (models.TextField): A PEM encoded client certificate used
            for authentication.
        ssl_client_key (models.TextField): A PEM encoded private key used for authentication.
        ssl_validation (models.BooleanField): If True, SSL peer validation must be performed.
        proxy_url (models.TextField): The optional proxy URL.
            Format: scheme://user:password@host:port
        username (models.TextField): The username to be used for authentication when syncing.
        password (models.TextField): The password to be used for authentication when syncing.
        download_policy (models.TextField): The policy for downloading content.
        last_synced (models.DatetimeField): Timestamp of the most recent successful sync.
        sync_mode (models.TextField) How the importer should sync from the upstream repository.

    Relations:

        repository (models.ForeignKey): The repository that owns this Importer
    """
    TYPE = 'importer'

    # Download Policies
    IMMEDIATE = 'immediate'
    ON_DEMAND = 'on_demand'
    BACKGROUND = 'background'
    DOWNLOAD_POLICIES = (
        (IMMEDIATE, 'Update the repository content and download all artifacts immediately.'),
        (ON_DEMAND, 'Update the repository content but no artifacts are downloaded.'),
        (BACKGROUND, 'Update the repository content and download artifacts in the background.'))

    # Sync Modes
    ADDITIVE = 'additive'
    MIRROR = 'mirror'
    SYNC_MODES = (
        (ADDITIVE, 'Add new content from the remote repository.'),
        (MIRROR, 'Add new content and remove content is no longer in the remote repository.'))

    def tls_storage_path(self, name):
        """
        Returns storage path for TLS file

        Args:
            name (str): Original name of the uploaded file.
        """
        return get_tls_path(self, name)

    # Setting this with "unique=True" will trigger a model validation warning, telling us that we
    # should use a OneToOneField here instead. While it is correct, doing it this way makes it
    # easy to allow multiple importers later: Move the 'repository' field from Importer and
    # Publisher to ContentAdaptor (without unique=True). This should make any migration that
    # allows multiple importers to be simple, since all that's needed is removing a constraint.
    # Using a OneToOneField here would break forward-compatibility with the idea of having
    # multiple importers associated with a Repository, since this exposes a ManyRelatedManager
    # on Repository with name "importers", and a OneToOneField would instead expose the single
    # related Importer instance.
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, unique=True)

    feed_url = models.TextField()
    validate = models.BooleanField(default=True)

    ssl_ca_certificate = models.FileField(blank=True, upload_to=tls_storage_path, max_length=255)
    ssl_client_certificate = models.FileField(blank=True, upload_to=tls_storage_path,
                                              max_length=255)
    ssl_client_key = models.FileField(blank=True, upload_to=tls_storage_path, max_length=255)
    ssl_validation = models.BooleanField(default=True)

    proxy_url = models.TextField(blank=True)
    username = models.TextField(blank=True)
    password = models.TextField(blank=True)

    download_policy = models.TextField(choices=DOWNLOAD_POLICIES)
    sync_mode = models.TextField(choices=SYNC_MODES)
    last_synced = models.DateTimeField(blank=True, null=True)

    class Meta(ContentAdaptor.Meta):
        default_related_name = 'importers'

    @property
    def is_deferred(self):
        """
        Get whether downloading is deferred.

        Returns:
            bool: True when deferred.
        """
        return self.download_policy != self.IMMEDIATE


class Publisher(ContentAdaptor):
    """
    A content publisher.

    Fields:

        auto_publish (models.BooleanField): Indicates that the adaptor may publish automatically
            when the associated repository's content has changed.
        last_published (models.DatetimeField): When the last successful publish occurred.

    Relations:

    """
    TYPE = 'publisher'

    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)

    auto_publish = models.BooleanField(default=True)
    last_published = models.DateTimeField(blank=True, null=True)

    class Meta(ContentAdaptor.Meta):
        default_related_name = 'publishers'


class RepositoryContent(Model):
    """
    Association between a repository and its contained content.

    Fields:

        created (models.DatetimeField): When the association was created.

    Relations:

        content (models.ForeignKey): The associated content.
        repository (models.ForeignKey): The associated repository.
        version_added (models.ForeignKey): The RepositoryVersion which added the referenced
            Content.
        version_removed (models.ForeignKey): The RepositoryVersion which removed the referenced
            Content.
    """
    content = models.ForeignKey('Content', on_delete=models.CASCADE,
                                related_name='version_memberships')
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)
    version_added = models.ForeignKey('RepositoryVersion', related_name='added_memberships')
    version_removed = models.ForeignKey('RepositoryVersion', null=True,
                                        related_name='removed_memberships')

    class Meta:
        unique_together = (('repository', 'content', 'version_added'),
                           ('repository', 'content', 'version_removed'))


class RepositoryVersion(Model):
    """
    A version of a repository's content set.
    Fields:
        number (models.PositiveIntegerField): A positive integer that uniquely identifies a version
            of a specific repository. Each new version for a repo should have this field set to
            1 + the most recent version.
        created (models.DateTimeField): When the version was created.
        action  (models.TextField): The action that produced the version.
    Relations:
        repository (models.ForeignKey): The associated repository.
    """
    repository = models.ForeignKey(Repository)
    number = models.PositiveIntegerField(db_index=True, default=1)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        default_related_name = 'versions'
        unique_together = ('repository', 'number')
        get_latest_by = 'number'
        ordering = ('number',)

    def content(self):
        """
        Returns:
            QuerySet: The Content objects that are related to this version.
        """
        relationships = RepositoryContent.objects.filter(
            repository=self.repository, version_added__number__lte=self.number).exclude(
            version_removed__number__lte=self.number
        )
        # Surely there is a better way to access the model. Maybe it should be in this module.
        content_model = self.repository.content.model
        # This causes a SQL subquery to happen.
        return content_model.objects.filter(version_memberships__in=relationships)

    @property
    def content_summary(self):
        """
        The contained content summary.

        Returns:
            dict: of {<type>: <count>}
        """
        mapping = self.content().values('type').annotate(count=models.Count('type'))
        return {m['type']: m['count'] for m in mapping}

    def added(self):
        """
        Returns:
            QuerySet: The Content objects that were added by this version.
        """
        # Surely there is a better way to access the model. Maybe it should be in this module.
        content_model = self.repository.content.model
        return content_model.objects.filter(version_memberships__version_added=self)

    def removed(self):
        """
        Returns:
            QuerySet: The Content objects that were removed by this version.
        """
        # Surely there is a better way to access the model. Maybe it should be in this module.
        content_model = self.repository.content.model
        return content_model.objects.filter(version_memberships__version_removed=self)

    def add_content(self, content):
        """
        Add a content unit to this version.

        Args:
            content (pulpcore.plugin.models.Content): a content model to add
        """
        # duplicates are ok
        with suppress(IntegrityError):
            association = RepositoryContent(
                repository=self.repository,
                content=content,
                version_added=self
            )
            association.save()

    def remove_content(self, content):
        """
        Remove content from the repository.

        Args:
            content (pulpcore.plugin.models.Content): A content model to remove
        """
        q_set = RepositoryContent.objects.filter(
            repository=self.repository,
            content=content,
            version_removed=None,
        )
        q_set.update(version_removed=self)

    def save(self, *args, **kwargs):
        """
        Save the version while setting the number automatically.
        """
        with suppress(self.DoesNotExist):
            self.number = self.repository.versions.latest().number + 1
        super().save(*args, **kwargs)

    def next(self):
        """
        Returns:
            RepositoryVersion: The next RepositoryVersion with the same repository.

        Raises:
            RepositoryVersion.DoesNotExist: if there is not a RepositoryVersion for the same
                repository and with a higher "number".
        """
        try:
            return self.repository.versions.filter(number__gt=self.number).order_by('number')[0]
        except IndexError:
            raise self.DoesNotExist
