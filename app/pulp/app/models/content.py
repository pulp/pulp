"""
Content related Django models.
"""
import hashlib

from django.db import models

from pulp.app.models import Model, MasterModel, Notes, GenericKeyValueRelation
from pulp.app.models.storage import StoragePath


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

    class Meta:
        verbose_name_plural = 'content'

    def natural_key(self):
        """
        Get the model's natural key based on natural_key_fields.

        :return: The natural key.
        :rtype: tuple
        """
        return tuple(getattr(self, f.name) for f in self.natural_key_fields)

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

    def __str__(self):
        cast = self.cast()

        # so here's a pretty good case for making namedtuples for content types
        # the third replacement string results in "natural_key_fieldname_0=repr(field_value), ..."
        natural_key_zip = zip(cast.natural_key_fields, cast.natural_key())
        natural_key_string = ', '.join(('='.join((t[0].name, repr(t[1]))) for t in natural_key_zip))
        return '<{} (type={}): {}>'.format(self._meta.object_name, cast.TYPE, natural_key_string)


class Artifact(Model):
    """
    A file associated with a piece of content.

    Fields:

        file (models.FileField): The stored file.
        downloaded (models.BooleanField): The associated file has been successfully downloaded.
        requested (models.BooleanField): The associated file has been requested by a client at
            least once.
        relative_path (models.TextField): The artifact's path relative to the associated
            :class:`Content`. This path is incorporated in the absolute storage path of the file
            and its published path relative to the root publishing directory. At a minimum the path
            will contain the file name but may also include sub-directories.
        size (models.IntegerField): The size of the file in bytes.
        md5 (models.CharField): The MD5 checksum of the file.
        sha1 (models.CharField): The SHA-1 checksum of the file.
        sha224 (models.CharField): The SHA-224 checksum of the file.
        sha256 (models.CharField): The SHA-256 checksum of the file.
        sha384 (models.CharField): The SHA-384 checksum of the file.
        sha512 (models.CharField): The SHA-512 checksum of the file.

    Relations:

        content (models.ForeignKey): The associated content.
    """

    # Note: The FileField does not support unique indexes and has
    # other undesirable behavior and complexities.  Using a custom
    # field should be investigated.

    file = models.FileField(db_index=True, upload_to=StoragePath(), max_length=255)
    downloaded = models.BooleanField(db_index=True, default=False)
    requested = models.BooleanField(db_index=True, default=False)
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
