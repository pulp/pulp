"""
Content related Django models.
"""
import hashlib

from django.contrib.contenttypes import fields
from django.db import models


from pulp.platform.models import Model, MasterModel, Notes
from pulp.platform.models.storage import StoragePath


class Content(MasterModel):
    """
    A piece of managed content.

    :cvar natural_key_fields: Tuple of natural fields.  Must be: models.Field.
    :type natural_key_fields: tuple

    Fields:

    :cvar type: The content type.
    :type type: models.TextField

    Relations:

    :cvar notes: Arbitrary information stored with the content.
    :type notes: fields.GenericRelation
    """
    natural_key_fields = ()

    type = models.TextField(blank=False, default=None)

    notes = fields.GenericRelation(Notes)

    def natural_key(self):
        """
        Get the model's natural key based on natural_key_fields.

        :return: The natural key.
        :rtype: tuple
        """
        return (getattr(self, f.name) for f in self.natural_key_fields)

    def natural_key_digest(self):
        """
        Get the SHA-256 digest of the natural key.
        The digest is updated with each field name followed by its value.
        The field names are only necessary to preserve backward compatibility
        with digests generated in pulp 2.

        :return: The hex digest.
        :rtype: str
        """
        h = hashlib.sha256()
        for name in sorted(f.name for f in self.natural_key_fields):
            h.update(name.encode(encoding='utf-8'))
            value = getattr(self, name)
            if isinstance(value, str):
                h.update(value.encode(encoding='utf-8'))
            else:
                h.update(value)
        return h.hexdigest()


class Artifact(Model):
    """
    A file associated with a piece of content.

    Fields:

    :cvar file: The stored file.
    :type file: models.FileField

    :cvar downloaded: The associated file has been successfully downloaded.
    :type downloaded: BooleanField

    :cvar relative_path: The artifact's path relative to the associated
                         :class:`Content`. This path is incorporated in
                         the absolute storage path of the file and its
                         published path relative to the root publishing
                         directory. At a minimum the path will contain the
                         file name but may also include sub-directories.
    :type relative_path: models.TextField

    :cvar size: The size of the file in bytes.
    :type size: models.IntegerField

    :cvar md5: The MD5 checksum of the file.
    :type md5: models.CharField

    :cvar sha1: The SHA-1 checksum of the file.
    :type sha1: models.CharField

    :cvar sha224: The SHA-224 checksum of the file.
    :type sha224: models.CharField

    :cvar sha256: The SHA-256 checksum of the file.
    :type sha256: models.CharField

    :cvar sha384: The SHA-384 checksum of the file.
    :type sha384: models.CharField

    :cvar sha512: The SHA-512 checksum of the file.
    :type sha512: models.CharField

    Relations:

    :cvar content: The associated content.
    :type content: Content
    """

    # Note: The FileField does not support unique indexes and has
    # other undesirable behavior and complexities.  Using a custom
    # field should be investigated.

    file = models.FileField(db_index=True, upload_to=StoragePath(), max_length=255)
    downloaded = models.BooleanField(db_index=True, default=False)
    relative_path = models.TextField(db_index=True, blank=False, default=None)

    size = models.IntegerField(blank=True, null=True)

    md5 = models.CharField(max_length=32, blank=True, null=True)
    sha1 = models.CharField(max_length=40, blank=True, null=True)
    sha224 = models.CharField(max_length=56, blank=True, null=True)
    sha256 = models.CharField(max_length=64, blank=True, null=True)
    sha384 = models.CharField(max_length=96, blank=True, null=True)
    sha512 = models.CharField(max_length=128, blank=True, null=True)

    content = models.ForeignKey(Content, related_name='artifacts', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('content', 'relative_path')

    def delete(self, *args, **kwargs):
        if self.downloaded:
            self.file.delete()
        super(Artifact, self).delete(*args, **kwargs)
