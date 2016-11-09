"""
Repository related Django models.
"""
from django.db import models
from django.utils import timezone

from pulp.app.models import Model, Notes, Scratchpad, MasterModel, GenericKeyValueRelation


class Repository(Model):
    """
    Collection of content.

    Fields:

        name (models.TextField): The repository name.
        description (models.TextField): An optional description.
        last_content_added (models.DateTimeField): When content was last added.
        last_content_removed (models.DatetimeField): When content was last removed.

    Relations:

        scratchpad (GenericKeyValueRelation): Arbitrary information stashed on the repository.
        notes (GenericKeyValueRelation): Arbitrary repository properties.
        content (models.ManyToManyField): Associated content.
    """
    name = models.TextField(db_index=True, unique=True)
    description = models.TextField(blank=True)

    last_content_added = models.DateTimeField(blank=True, null=True)
    last_content_removed = models.DateTimeField(blank=True, null=True)

    scratchpad = GenericKeyValueRelation(Scratchpad)
    notes = GenericKeyValueRelation(Notes)

    content = models.ManyToManyField('Content', through='RepositoryContent',
                                     related_name='repositories')

    class Meta:
        verbose_name_plural = 'repositories'

    @property
    def content_summary(self):
        """
        The contained content summary.

        :return: A dict of {<type>: <count>}
        :rtype:  dict
        """
        mapping = self.content.values('type').annotate(count=models.Count('type'))
        return {m['type']: m['count'] for m in mapping}

    def natural_key(self):
        """
        Get the model's natural key.

        :return: The model's natural key.
        :rtype: tuple
        """
        return (self.name,)

    def __str__(self):
        return "<{}: {}>".format(self._meta.model.__name__, self.name)


class RepositoryGroup(Model):
    """
    A group of repositories.

    Fields:

        name (models.TextField): The group name.
        description (models.TextField): An optional description.

    Relations:
        notes (GenericKeyValueRelation): Arbitrary group properties.
        members (models.ManyToManyField): Repositories associated with the group.
    """
    name = models.TextField(db_index=True, unique=True)
    description = models.TextField(blank=True)

    members = models.ManyToManyField('Repository')
    scratchpad = GenericKeyValueRelation(Scratchpad)
    notes = GenericKeyValueRelation(Notes)

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

    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)

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
        validate (models.BooleanField): Validate the imported context.
        ssl_ca_certificate (models.TextField): A PEM encoded CA certificate used to validate the
            server certificate presented by the external source.
        ssl_client_certificate (models.TextField): A PEM encoded client certificate used
            for authentication.
        ssl_client_key (models.TextField): A PEM encoded private key used for authentication.
        ssl_validation (models.BooleanField): Indicates whether SSL peer validation
            must be performed.
        proxy_url (models.TextField): The optional proxy URL.
            Format: scheme://user:password@host:port
        basic_auth_user (models.TextField): The user used in HTTP basic authentication.
        basic_auth_password (models.TextField): The password used in HTTP basic authentication.
        max_download_bandwidth (models.IntegerField): The max amount of bandwidth used per download
            in bytes per second.
        max_concurrent_downloads (models.IntegerField): The number of concurrent downloads
            permitted.
        download_policy (models.TextField): The policy for downloading content.
        last_sync (models.DatetimeField): When the last successful synchronization occurred.

    Relations:

        scratchpad (GenericKeyValueRelation): Arbitrary information stashed by the importer.
    """
    TYPE = 'importer'

    # Download Policies
    IMMEDIATE = 'immediate'
    ON_DEMAND = 'on_demand'
    BACKGROUND = 'background'
    DOWNLOAD_POLICIES = (
        (IMMEDIATE, 'Download Immediately'),
        (ON_DEMAND, 'Download On Demand'),
        (BACKGROUND, 'Download In Background'))

    feed_url = models.TextField()
    validate = models.BooleanField(default=True)

    ssl_ca_certificate = models.TextField(blank=True)
    ssl_client_certificate = models.TextField(blank=True)
    ssl_client_key = models.TextField(blank=True)
    ssl_validation = models.BooleanField(default=True)

    proxy_url = models.TextField(blank=True)

    basic_auth_user = models.TextField(blank=True)
    basic_auth_password = models.TextField(blank=True)

    max_download_bandwidth = models.IntegerField(null=True)
    max_concurrent_downloads = models.IntegerField(null=True)

    download_policy = models.TextField(choices=DOWNLOAD_POLICIES)
    last_sync = models.DateTimeField(blank=True, null=True)

    scratchpad = GenericKeyValueRelation(Scratchpad)

    class Meta(ContentAdaptor.Meta):
        default_related_name = 'importers'


class Publisher(ContentAdaptor):
    """
    A content publisher.

    Fields:

        auto_publish (models.BooleanField): Indicates that the adaptor may publish automatically
            when the associated repository's content has changed.
        relative_path (models.TextField): The (relative) path component of the published url.
        last_published (models.DatetimeField): When the last successful publish occurred.

    Relations:

    """
    TYPE = 'publisher'

    auto_publish = models.BooleanField(default=True)
    relative_path = models.TextField(blank=True)
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
    """
    content = models.ForeignKey('Content', on_delete=models.CASCADE)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        """
        Save the association.
        """
        self.repository.last_content_added = timezone.now()
        self.repository.save()
        super(RepositoryContent, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Delete the association.
        """
        self.repository.last_content_removed = timezone.now()
        self.repository.save()
        super(RepositoryContent, self).delete(*args, **kwargs)
