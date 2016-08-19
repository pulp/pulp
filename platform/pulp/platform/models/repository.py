"""
Repository related Django models.
"""
from django.db import models
from django.contrib.contenttypes import fields
from django.utils import timezone

from pulp.platform.models import Model, Notes, Scratchpad, MasterModel


class Content(Model):
    # placeholder
    type = models.TextField()
    created = models.DateTimeField(auto_now_add=True)


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


class Plugin(MasterModel):
    """
    An Abstract model for plugins.

    Fields:

    :cvar name: The plugin name.
    :type type: models.TextField

    :cvar type: The plugin type.
    :type type: models.TextField

    :cvar last_updated: When the plugin was last updated.
    :type last_updated: fields.DateTimeField

    Relations:

    """
    name = models.TextField(db_index=True)
    type = models.TextField(blank=False, default=None)
    last_updated = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        abstract = True


class Importer(Plugin):
    """
    A abstract content importer.

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

    class Meta:
        abstract = True
        unique_together = ('name', 'repository')


class RepositoryImporter(Importer):
    """
    A content importer that is associated with a repository..

    Fields:

    Relations:

    :cvar repository: The associated repository.
    :type repository: models.ForeignKey
    """

    repository = models.ForeignKey(
        Repository, related_name='importers', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'repository')


class Distributor(Plugin):
    """
    An abstract content distributor.

    Fields:

    :cvar relative_path: The (relative) path component of the published url.
    :type relative_path: models.TextField

    :cvar last_published: When the last successful publish occurred.
    :type last_published: models.DateTimeField

    Relations:

    """
    relative_path = models.TextField(blank=True)
    last_published = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True


class RepositoryDistributor(Distributor):
    """
    A content distributor that is associated with a repository.

    Fields:

    :cvar auto_publish: Indicates that the distributor may publish automatically
        when the associated repository's content has changed.
    :type auto_publish: models.BooleanField

    Relations:

    :cvar repository: The associated repository.
    :type repository: models.ForeignKey

    """
    auto_publish = models.BooleanField(default=True)

    repository = models.ForeignKey(
        Repository, related_name='distributors', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'repository')


class GroupDistributor(Distributor):
    """
    A content distributor that is associated with a repository group.

    Fields:

    Relations:

    :cvar group: The associated repository group.
    :type group: models.ForeignKey

    """
    group = models.ForeignKey(
        RepositoryGroup, related_name='distributors', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'group')


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
