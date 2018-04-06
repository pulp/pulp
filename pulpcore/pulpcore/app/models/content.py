"""
Content related Django models.
"""
from django.core import validators
from django.db import models
from itertools import chain

from pulpcore.app.models import Model, MasterModel, Notes, GenericKeyValueRelation, storage, fields


class Artifact(Model):
    """
    A file associated with a piece of content.

    When creating an Artifact, the file provided is moved into place by Pulp.

    Fields:

        file (models.FileField): The stored file. This field should be set using an absolute path to
            a temporary file. It also accepts `class:django.core.files.File`.
        size (models.IntegerField): The size of the file in bytes.
        md5 (models.CharField): The MD5 checksum of the file.
        sha1 (models.CharField): The SHA-1 checksum of the file.
        sha224 (models.CharField): The SHA-224 checksum of the file.
        sha256 (models.CharField): The SHA-256 checksum of the file.
        sha384 (models.CharField): The SHA-384 checksum of the file.
        sha512 (models.CharField): The SHA-512 checksum of the file.
    """
    def storage_path(self, name):
        """
        Callable used by FileField to determine where the uploaded file should be stored.

        Args:
            name (str): Original name of uploaded file. It is ignored by this method because the
                sha256 checksum is used to determine a file path instead.
        """
        return storage.get_artifact_path(self.sha256)

    file = fields.ArtifactFileField(blank=False, null=False, upload_to=storage_path, max_length=255)
    size = models.IntegerField(blank=False, null=False)
    md5 = models.CharField(max_length=32, blank=False, null=False, unique=False, db_index=True)
    sha1 = models.CharField(max_length=40, blank=False, null=False, unique=False, db_index=True)
    sha224 = models.CharField(max_length=56, blank=False, null=False, unique=False, db_index=True)
    sha256 = models.CharField(max_length=64, blank=False, null=False, unique=True, db_index=True)
    sha384 = models.CharField(max_length=96, blank=False, null=False, unique=True, db_index=True)
    sha512 = models.CharField(max_length=128, blank=False, null=False, unique=True, db_index=True)

    # All digest fields ordered by algorithm strength.
    DIGEST_FIELDS = (
        'sha512',
        'sha384',
        'sha256',
        'sha224',
        'sha1',
        'md5',
    )

    # Reliable digest fields ordered by algorithm strength.
    RELIABLE_DIGEST_FIELDS = DIGEST_FIELDS[:-3]

    def is_equal(self, other):
        """
        Is equal by matching digest.

        Args:
            other (pulpcore.app.models.Artifact): A artifact to match.

        Returns:
            bool: True when equal.
        """
        for field in Artifact.RELIABLE_DIGEST_FIELDS:
            digest = getattr(self, field)
            if not digest:
                continue
            if digest == getattr(other, field):
                return True
        return False

    def save(self, *args, **kwargs):
        """
        Saves Artifact model and closes the file associated with the Artifact

        Args:
            args (list): list of positional arguments for Model.save()
            kwargs (dict): dictionary of keyword arguments to pass to Model.save()
        """
        try:
            super().save(*args, **kwargs)
            self.file.close()
        except Exception:
            self.file.close()
            raise

    def delete(self, *args, **kwargs):
        """
        Deletes Artifact model and the file associated with the Artifact

        Args:
            args (list): list of positional arguments for Model.delete()
            kwargs (dict): dictionary of keyword arguments to pass to Model.delete()
        """
        super().delete(*args, **kwargs)
        self.file.delete(save=False)


class Content(MasterModel):
    """
    A piece of managed content.

    Relations:

        notes (GenericKeyValueRelation): Arbitrary information stored with the content.
        artifacts (models.ManyToManyField): Artifacts related to Content through ContentArtifact
    """
    TYPE = 'content'

    notes = GenericKeyValueRelation(Notes)
    artifacts = models.ManyToManyField(Artifact, through='ContentArtifact')

    class Meta:
        verbose_name_plural = 'content'
        unique_together = ()

    @classmethod
    def natural_key_fields(cls):
        """
        Returns a tuple of the natural key fields which usually equates to unique_together fields
        """
        return tuple(chain.from_iterable(cls._meta.unique_together))

    def natural_key(self):
        """
        Get the model's natural key based on natural_key_fields.

        :return: The natural key.
        :rtype: tuple
        """
        return tuple(getattr(self, f) for f in self.natural_key_fields())


class ContentArtifact(Model):
    """
    A relationship between a Content and an Artifact.

    Serves as a through model for the 'artifacts' ManyToManyField in Content.
    Artifact is protected from deletion if it's present in a ContentArtifact relationship.
    """
    artifact = models.ForeignKey(Artifact, on_delete=models.PROTECT, null=True)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    relative_path = models.CharField(max_length=256)

    class Meta:
        unique_together = ('content', 'relative_path')


class RemoteArtifact(Model):
    """
    Represents a content artifact that is provided by a remote (external) repository.

    Remotes that want to support deferred download policies should use this model to store
    information required for downloading an Artifact at some point in the future. At a minimum this
    includes the URL, the ContentArtifact, and the Remote that created it. It can also store
    expected size and any expected checksums.

    Fields:

        url (models.TextField): The URL where the artifact can be retrieved.
        size (models.IntegerField): The expected size of the file in bytes.
        md5 (models.CharField): The expected MD5 checksum of the file.
        sha1 (models.CharField): The expected SHA-1 checksum of the file.
        sha224 (models.CharField): The expected SHA-224 checksum of the file.
        sha256 (models.CharField): The expected SHA-256 checksum of the file.
        sha384 (models.CharField): The expected SHA-384 checksum of the file.
        sha512 (models.CharField): The expected SHA-512 checksum of the file.

    Relations:

        content_artifact (:class:`pulpcore.app.models.GenericKeyValueRelation`): Arbitrary
            information stored with the content.
        remote (:class:`django.db.models.ForeignKey`): Remote that created the
            RemoteArtifact.
    """
    url = models.TextField(blank=True, validators=[validators.URLValidator])
    size = models.IntegerField(blank=True, null=True)
    md5 = models.CharField(max_length=32, blank=True, null=True)
    sha1 = models.CharField(max_length=40, blank=True, null=True)
    sha224 = models.CharField(max_length=56, blank=True, null=True)
    sha256 = models.CharField(max_length=64, blank=True, null=True)
    sha384 = models.CharField(max_length=96, blank=True, null=True)
    sha512 = models.CharField(max_length=128, blank=True, null=True)

    content_artifact = models.ForeignKey(ContentArtifact, on_delete=models.CASCADE)
    remote = models.ForeignKey('Remote', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('content_artifact', 'remote')
