"""
Content related Django models.
"""
from django.core import validators
from django.core.files.storage import default_storage
from django.db import models


from pulpcore.app.models import Model, MasterModel, Notes, GenericKeyValueRelation


class Artifact(Model):
    """
    A file associated with a piece of content.

    Fields:

        file (models.FileField): The stored file.
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
        return default_storage.get_artifact_path(self.sha256)

    file = models.FileField(db_index=True, upload_to=storage_path, max_length=255)
    size = models.IntegerField(blank=False, null=False)
    md5 = models.CharField(max_length=32, blank=False, null=False, unique=False, db_index=True)
    sha1 = models.CharField(max_length=40, blank=False, null=False, unique=False, db_index=True)
    sha224 = models.CharField(max_length=56, blank=False, null=False, unique=False, db_index=True)
    sha256 = models.CharField(max_length=64, blank=False, null=False, unique=True, db_index=True)
    sha384 = models.CharField(max_length=96, blank=False, null=False, unique=True, db_index=True)
    sha512 = models.CharField(max_length=128, blank=False, null=False, unique=True, db_index=True)


class Content(MasterModel):
    """
    A piece of managed content.

    Attributes:

        natural_key_fields (tuple): Natural key fields.  Must be models.Field subclasses.

    Relations:

        notes (GenericKeyValueRelation): Arbitrary information stored with the content.
    """
    TYPE = 'content'

    natural_key_fields = ()

    notes = GenericKeyValueRelation(Notes)
    artifacts = models.ManyToManyField(Artifact, through='ContentArtifact')

    class Meta:
        verbose_name_plural = 'content'

    def natural_key(self):
        """
        Get the model's natural key based on natural_key_fields.

        :return: The natural key.
        :rtype: tuple
        """
        return tuple(getattr(self, f.name) for f in self.natural_key_fields)


class ContentArtifact(Model):
    """
    A relationship between a Content and an Artifact.

    Serves as a through model for the 'artifacts' ManyToManyField in Content.
    """
    def storage_path(self, name):
        """
        Callable used by FileField to determine where the uploaded file should be stored.

        Args:
            name (str): Original name of uploaded file. It is ignored by this method because the
                sha256 checksum is used to determine a file path instead.
        """
        return default_storage.get_artifact_path(self.sha256)

    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE, null=True)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    relative_path = models.CharField(max_length=64)


class DeferredArtifact(Model):
    """
    A URL for fetching a file associated with a piece of content.

    Fields:

        url (models.TextField): The URL where the artifact can be retrieved.
        size (models.IntegerField): The expected size of the file in bytes.
        md5 (models.CharField): The expected MD5 checksum of the file.
        sha1 (models.CharField): The expected SHA-1 checksum of the file.
        sha224 (models.CharField): The expected SHA-224 checksum of the file.
        sha256 (models.CharField): The expected SHA-256 checksum of the file.
        sha384 (models.CharField): The expected SHA-384 checksum of the file.
        sha512 (models.CharField): The expected SHA-512 checksum of the file.
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
    importer = models.ForeignKey('Importer', on_delete=models.CASCADE)
