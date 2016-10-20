from rest_framework import serializers

from pulp.app import models
from pulp.app.serializers import base, fields, generic


class ContentSerializer(base.MasterModelSerializer):
    _href = base.DetailIdentityField()
    repositories = fields.RepositoryRelatedField(many=True)
    notes = generic.NotesKeyValueRelatedField()
    artifacts = serializers.HyperlinkedRelatedField(
        help_text="The associated files.",
        many=True,
        read_only=True,
        view_name='artifacts-detail'
    )

    class Meta:
        model = models.Content
        fields = base.MasterModelSerializer.Meta.fields + ('repositories', 'notes', 'artifacts')


class ArtifactSerializer(base.ModelSerializer):
    file = serializers.FileField(
        help_text="The stored file.",
        read_only=True
    )

    downloaded = serializers.BooleanField(
        help_text="An indication that the associated file has been downloaded.",
        read_only=True
    )

    requested = serializers.BooleanField(
        help_text="An indication that the associated file has been requested by a client.",
        read_only=True
    )

    relative_path = serializers.CharField(
        help_text="The relative path of the artifact which is incorporated into the storage and"
                  " published paths.",
        read_only=True
    )

    size = serializers.IntegerField(
        help_text="The size of the file in bytes.",
        read_only=True
    )

    md5 = serializers.CharField(
        help_text="The MD5 checksum of the file if available.",
        read_only=True,
        required=False
    )

    sha1 = serializers.CharField(
        help_text="The SHA-1 checksum of the file if available.",
        read_only=True,
        required=False
    )

    sha224 = serializers.CharField(
        help_text="The SHA-224 checksum of the file if available.",
        read_only=True,
        required=False
    )

    sha256 = serializers.CharField(
        help_text="The SHA-256 checksum of the file if available.",
        read_only=True,
        required=False
    )

    sha384 = serializers.CharField(
        help_text="The SHA-384 checksum of the file if available.",
        read_only=True,
        required=False
    )

    sha512 = serializers.CharField(
        help_text="The SHA-512 checksum of the file if available.",
        read_only=True,
        required=False
    )

    class Meta:
        model = models.Artifact
        fields = base.ModelSerializer.Meta.fields + ('file', 'downloaded', 'requested',
                                                     'relative_path', 'size', 'md5', 'sha1',
                                                     'sha224', 'sha256', 'sha384', 'sha512')
