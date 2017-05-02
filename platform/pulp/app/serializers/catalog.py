from gettext import gettext as _

from rest_framework import serializers

from pulp.app import models
from pulp.app.serializers import ModelSerializer, DetailRelatedField


class DownloadCatalogSerializer(ModelSerializer):
    url = serializers.CharField(
        help_text=_("The URL used to download the related artifact."),
        allow_blank=True, read_only=True,
    )

    artifact = serializers.HyperlinkedRelatedField(
        help_text=_("The artifact that is expected to be present at url"),
        queryset=models.Artifact.objects.all(),
        view_name="artifact-details"
    )

    importer = DetailRelatedField(
        help_text=_("The importer that contains the configuration necessary to access url."),
        queryset=models.Importer.objects.all(),
        view_name="importer-details"
    )

    class Meta:
        model = models.DownloadCatalog
        fields = ModelSerializer.Meta.fields + ("artifact", "importer", "url",)
