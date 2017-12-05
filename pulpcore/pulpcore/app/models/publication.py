from django.db import models

from pulpcore.app.models import Model, storage


class Publication(Model):
    """
    Fields:
        created (models.DatetimeField): When the publication was created UTC.

    Relations:
        publisher (models.ForeignKey): The publisher that created the publication.
    """

    created = models.DateTimeField(auto_now_add=True)

    publisher = models.ForeignKey('Publisher', on_delete=models.CASCADE)


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
        auto_updated (models.BooleanField): The publication is updated automatically
            whenever the publisher has created a new publication.
        http (models.BooleanField): The publication is distributed using HTTP.
        https (models.BooleanField): The publication is distributed using HTTPS.

    Relations:
        publisher (models.ForeignKey): The associated publisher.
            The publication is automatically set to the latest publication created
            by the specified publisher.
        publication (models.ForeignKey): The current publication associated with
            the distribution.  This is the publication being served by Pulp through
            this relative URL path and settings.
    """

    name = models.CharField(max_length=255, unique=True)
    base_path = models.CharField(max_length=255, unique=True)
    auto_updated = models.BooleanField(default=True)
    http = models.BooleanField(default=True)
    https = models.BooleanField(default=True)

    publication = models.ForeignKey(Publication, null=True, on_delete=models.SET_NULL)
    publisher = models.ForeignKey('Publisher', null=True, on_delete=models.SET_NULL)

    class Meta:
        default_related_name = 'distributions'
