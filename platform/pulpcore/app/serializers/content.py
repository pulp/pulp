from gettext import gettext as _
import hashlib

from rest_framework import serializers
from rest_framework.validators import UniqueValidator


from pulpcore.app import models
from pulpcore.app.serializers import base, fields, generic


UNIQUE_ALGORITHMS = ['sha256', 'sha384', 'sha512']


class ContentSerializer(base.MasterModelSerializer):
    _href = base.DetailIdentityField()
    notes = generic.NotesKeyValueRelatedField()
    artifacts = fields.ContentArtifactsField(
        help_text=_("A dict mapping relative paths inside the Content to the corresponding"
                    "Artifact URLs. E.g.: {'relative/path': "
                    "'http://localhost/full_artifact_path'}"),
    )

    class Meta:
        model = models.Content
        fields = base.MasterModelSerializer.Meta.fields + ('notes', 'artifacts')


class ArtifactSerializer(base.ModelSerializer):
    _href = serializers.HyperlinkedIdentityField(
        view_name='artifacts-detail',
    )

    file = serializers.FileField(
        help_text=_("The stored file."),
        required=True
    )

    size = serializers.IntegerField(
        help_text=_("The size of the file in bytes."),
        required=False
    )

    md5 = serializers.CharField(
        help_text=_("The MD5 checksum of the file if available."),
        required=False
    )

    sha1 = serializers.CharField(
        help_text=_("The SHA-1 checksum of the file if available."),
        required=False
    )

    sha224 = serializers.CharField(
        help_text=_("The SHA-224 checksum of the file if available."),
        required=False
    )

    sha256 = serializers.CharField(
        help_text=_("The SHA-256 checksum of the file if available."),
        required=False
    )

    sha384 = serializers.CharField(
        help_text=_("The SHA-384 checksum of the file if available."),
        required=False
    )

    sha512 = serializers.CharField(
        help_text=_("The SHA-512 checksum of the file if available."),
        required=False
    )

    def validate(self, data):
        """
        Validate file by size and by all checksums provided.

        Args:
            data (:class:`django.http.QueryDict`): QueryDict mapping Artifact model fields to their
                values

        Raises:
            :class:`rest_framework.exceptions.ValidationError`: When the expected file size or any
                of the checksums don't match their actual values.
        """
        if 'size' in data:
            if data['file'].size != int(data['size']):
                raise serializers.ValidationError(_("The size did not match actual size of file."))
        else:
            data['size'] = data['file'].size

        for algorithm in hashlib.algorithms_guaranteed:
            digest = data['file'].hashers[algorithm].hexdigest()

            if algorithm in data and digest != data[algorithm]:
                raise serializers.ValidationError(_("The %s checksum did not match.") % algorithm)
            else:
                data[algorithm] = digest
            if algorithm in UNIQUE_ALGORITHMS:
                validator = UniqueValidator(models.Artifact.objects.all(),
                                            message=_("{0} checksum must be "
                                                      "unique.").format(algorithm))
                validator.field_name = algorithm
                validator.instance = None
                validator(digest)
        return data

    class Meta:
        model = models.Artifact
        fields = base.ModelSerializer.Meta.fields + ('file', 'size', 'md5', 'sha1', 'sha224',
                                                     'sha256', 'sha384', 'sha512')
