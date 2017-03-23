"""
The plugin should implement a serializer for each of the models that will be exposed to the API.
These serializers should choose the matching base class from `pulp.app.serializers`.
"""
from pulp.app.serializers import ContentSerializer, ImporterSerializer

from pulp.app.tests.testapp.models import TestContent, TestImporter

from rest_framework import serializers


class TestContentSerializer(ContentSerializer):
    class Meta:
        fields = ContentSerializer.Meta.fields + ('name',)
        model = TestContent


class TestImporterSerializer(ImporterSerializer):
    """
    Example of a Detail serializer.
    """
    # _href should be provided by the base class, but somewhere up in the inheritance the view_name
    # will default to `testimporter-detail`, which is a bug. This should be removed when issue
    # TODO(asmacdo)link is fixed.
    _href = serializers.HyperlinkedIdentityField(
        view_name='importers-test-detail',
    )

    class Meta:
        model = TestImporter
        fields = ImporterSerializer.Meta.fields
