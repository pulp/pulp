from gettext import gettext as _

from rest_framework import serializers

from pulpcore.app import models
from pulpcore.app.serializers import ModelSerializer, DetailNestedHyperlinkedRelatedField


class DownloadCatalogSerializer(ModelSerializer):

    _href = serializers.HyperlinkedIdentityField(
        view_name='downloadcatalogs-detail',
    )

    url = serializers.CharField(
        help_text=_("The URL used to download the related artifact."),
        allow_blank=True, read_only=True,
    )

    artifact = serializers.HyperlinkedRelatedField(
        help_text=_("The artifact that is expected to be present at url"),
        queryset=models.Artifact.objects.all(),
        view_name="artifacts-detail"
    )

    importer = DetailNestedHyperlinkedRelatedField(
        parent_lookup_kwargs={'repository_name': 'repository__name'},
        queryset=models.Importer.objects.all(),
        help_text=_("The importer that contains the configuration necessary to access url."),
        lookup_field='name'
    )

    class Meta:
        model = models.DownloadCatalog
        fields = ModelSerializer.Meta.fields + ("artifact", "importer", "url",)
