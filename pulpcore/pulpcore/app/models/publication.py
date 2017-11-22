from django.db import models

from pulpcore.app.models import Model, storage


class Publication(Model):
    """
    Fields:
        created (models.DatetimeField): When the publication was created UTC.

    Relations:
        publisher (models.ForeignKey): The publisher that created the publication.
        repo_version (models.ForeignKey): The RepositoryVersion whose content set was used to
            create this Publication.
    """

    created = models.DateTimeField(auto_now_add=True)

    publisher = models.ForeignKey('Publisher', on_delete=models.CASCADE)

    repo_version = models.ForeignKey('RepositoryVersion', on_delete=models.CASCADE)


class PublishedFile(Model):
    """
    A file included in Publication.

    Fields:
        relative_path (models.CharField): The (relative) path component of the published url.

    Relations:
        publication (models.ForeignKey): The publication in which the artifact is included.

    """
    relative_path = models.CharField(max_length=255)

    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class PublishedArtifact(PublishedFile):
    """
    An artifact that is part of a publication.

    Relations:
        content_artifact (models.ForeignKey): The referenced content artifact.
    """
    content_artifact = models.ForeignKey('ContentArtifact', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('publication', 'content_artifact')
        default_related_name = 'published_artifact'


class PublishedMetadata(PublishedFile):
    """
    Metadata file that is part of a publication.

    Fields:
        file (models.FileField): The stored file.
    """

    def _storage_path(self, name):
        return storage.published_metadata_path(self, name)

    file = models.FileField(upload_to=_storage_path, max_length=255)

    class Meta:
        unique_together = ('publication', 'file')
        default_related_name = 'published_metadata'


class Distribution(Model):
    """
    A distribution defines how a publication is distributed by pulp.

    Fields:
        name (models.CharField): The name of the distribution.
            Examples: "rawhide" and "stable".
        base_path (models.CharField): The base (relative) path component of the published url.
        http (models.BooleanField): The publication is distributed using HTTP.
        https (models.BooleanField): The publication is distributed using HTTPS.

    Relations:
        publisher (models.ForeignKey): The associated publisher.
            All publications created by the specified publisher will be automatically associated.
        publication (models.ForeignKey): The current publication associated with
            the distribution.  This is the publication being served by Pulp through
            this relative URL path and settings.
    """

    name = models.CharField(max_length=255)
    base_path = models.CharField(max_length=255, unique=True)
    http = models.BooleanField(default=False)
    https = models.BooleanField(default=True)

    publication = models.ForeignKey(Publication, null=True, on_delete=models.SET_NULL)
    publisher = models.ForeignKey('Publisher', null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('publisher', 'name')
        default_related_name = 'distributions'
