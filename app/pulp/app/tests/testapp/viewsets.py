"""
Each model also requires a ViewSet so that they may be handled by the API. Inherit the
matching base class from `pulp.app.viewsets`. `endpoint_name` should by convention match the type
of the content returned by the queryset.
"""
from pulp.app import viewsets

from pulp.app.tests.testapp.models import TestContent, TestImporter
from pulp.app.tests.testapp.serializers import TestContentSerializer, TestImporterSerializer


class TestContentViewSet(viewsets.ContentViewSet):
    endpoint_name = 'test'
    queryset = TestContent.objects.all()
    serializer_class = TestContentSerializer


class TestImporterViewSet(viewsets.ImporterViewSet):
    # Endpoint name is appened to the `importers/` endpoint and should indicate importer type. In
    # this case, importers of TestContent will be of type `test`.
    endpoint_name = 'test'
    queryset = TestImporter.objects.all()
    serializer_class = TestImporterSerializer
