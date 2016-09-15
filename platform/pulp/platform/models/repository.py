"""
Repository related Django models.
"""
from django.db import models
from django.contrib.contenttypes import fields
from django.utils import timezone

from pulp.platform.models import Model, Notes, Scratchpad, MasterModel


class Repository(Model):
    """
    Collection of content.

    Fields:

    :cvar name: The repository name.
    :type name: models.TextField

    :cvar: description: An optional description.
    :type: models.TextField

    :cvar last_content_added: When content was last added.
    :type last_content_added: models.DateTimeField

    :cvar last_content_removed: When content was last removed.
    :type last_content_removed: models.DateTimeField

    Relations:

    :cvar scratchpad: Arbitrary information stashed on the repository.
    :type scratchpad: fields.GenericRelation

    :cvar notes: Arbitrary repository properties.
    :type notes: fields.GenericRelation

    :cvar content: Associated content.
    :type content: models.ManyToManyField
    """
    name = models.TextField(db_index=True, unique=True)
    description = models.TextField(blank=True)

    last_content_added = models.DateTimeField(blank=True, null=True)
    last_content_removed = models.DateTimeField(blank=True, null=True)

    scratchpad = fields.GenericRelation(Scratchpad)
    notes = fields.GenericRelation(Notes)

    content = models.ManyToManyField('Content', through='RepositoryContent')

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


class RepositoryGroup(Model):
    """
    A group of repositories.

    Fields:

    :cvar name: The group name.
    :type name: models.TextField

    :cvar: description: An optional description.
    :type: models.TextField

    Relations:
    :cvar notes: Arbitrary group properties.
    :type notes: fields.GenericRelation

    :cvar members: Repositories associated with the group.
    :type members: models.ManyToManyField
    """
    name = models.TextField(db_index=True, unique=True)
    description = models.TextField(blank=True)

    members = models.ManyToManyField('Repository')
    scratchpad = fields.GenericRelation(Scratchpad)
    notes = fields.GenericRelation(Notes)

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

    :cvar name: The ContentAdaptor name.
    :type type: models.TextField

    :cvar type: The ContentAdaptor type.
    :type type: models.TextField

    :cvar last_updated: When the adaptor was last updated.
    :type last_updated: fields.DateTimeField

    Relations:

    :cvar repository: The associated repository.
    :type repository: models.ForeignKey

    """
    name = models.TextField(db_index=True)
    type = models.TextField(blank=False, default=None)
    last_updated = models.DateTimeField(auto_now=True, blank=True, null=True)

    repository = models.ForeignKey(Repository, related_name='%(class)ss', on_delete=models.CASCADE)

    class Meta:
        abstract = True
        unique_together = ('repository', 'name')

    def natural_key(self):
        """
        Get the model's natural key.

        :return: The model's natural key.
        :rtype: tuple
        """
        return (self.repository, self.name)


class Importer(ContentAdaptor):
    """
    A content importer.

    Fields:

    :cvar feed_url: The URL of an external content source.
    :type feed_url: models.TextField

    :cvar validate: Validate the imported context.
    :type validate: models.BooleanField

    :cvar ssl_ca_certificate: A PEM encoded CA certificate used to validate the server
                              certificate presented by the external source.
    :type ssl_ca_certificate: models.TextField

    :cvar ssl_client_certificate: A PEM encoded client certificate used for authentication.
    :type ssl_client_certificate: models.TextField

    :cvar ssl_client_key: A PEM encoded private key used for authentication.
    :type ssl_client_key: models.TextField

    :cvar ssl_validation: Indicates whether SSL peer validation must be performed.
    :type ssl_validation: models.BooleanField

    :cvar proxy_url: The optional proxy URL. Format: scheme://user:password@host:port
    :type proxy_url: models.ForeignKey

    :cvar basic_auth_user: The user used in HTTP basic authentication.
    :type basic_auth_user: models.TextField

    :cvar basic_auth_password: The password used in HTTP basic authentication.
    :type basic_auth_password: models.TextField

    :cvar max_download_bandwidth: The max amount of bandwidth used per download (Bps).
    :type max_download_bandwidth: models.IntegerField

    :cvar max_concurrent_downloads: The number of concurrent downloads permitted.
    :type max_concurrent_downloads: models.IntegerField

    :cvar download_policy: The policy for downloading content.
    :type download_policy: models.TextField

    :cvar last_sync: When the last successful synchronization occurred.
    :type last_sync: models.DateTimeField

    Relations:

    :cvar scratchpad: Arbitrary information stashed by the importer.
    :type scratchpad: fields.GenericRelation
    """

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

    scratchpad = fields.GenericRelation(Scratchpad)


class Publisher(ContentAdaptor):
    """
    A content publisher.

    Fields:

    :cvar auto_publish: Indicates that the adaptor may publish automatically
        when the associated repository's content has changed.
    :type auto_publish: models.BooleanField

    :cvar relative_path: The (relative) path component of the published url.
    :type relative_path: models.TextField

    :cvar last_published: When the last successful publish occurred.
    :type last_published: models.DateTimeField

    Relations:

    """
    auto_publish = models.BooleanField(default=True)
    relative_path = models.TextField(blank=True)
    last_published = models.DateTimeField(blank=True, null=True)


class RepositoryContent(Model):
    """
    Association between a repository and its contained content.

    Fields:

    :cvar created: When the association was created.
    :type created: fields.DateTimeField

    Relations:

    :cvar content: The associated content.
    :type content: models.ForeignKey

    :cvar repository: The associated repository.
    :type repository: models.ForeignKey
    """
    created = models.DateTimeField(auto_now_add=True)

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
