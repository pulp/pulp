from django_filters.rest_framework import filterset
from rest_framework import status
from rest_framework.response import Response


from pulpcore.app.models import Artifact, Content
from pulpcore.app.serializers import ArtifactSerializer, ContentSerializer
from pulpcore.app.viewsets import NamedModelViewSet


class ContentFilter(filterset.FilterSet):
    """
    Plugin content filters would need:
     - to inherit from this class
     - to add any plugin-specific filters if needed
     - to define its own `Meta` class which needs:

       - to specify plugin content model
       - to extend `fields` with plugin-specific ones
    """
    class Meta:
        model = Content
        fields = ['type']


class ArtifactFilter(filterset.FilterSet):
    """
    Artifact filter Plugin content filters would need:
     - to inherit from this class
     - to add any plugin-specific filters if needed
     - to define its own `Meta` class which needs:

       - to specify plugin content model
       - to extend `fields` with plugin-specific ones
    """
    class Meta:
        model = Artifact
        fields = ['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512']


class ContentViewSet(NamedModelViewSet):
    endpoint_name = 'content'
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    filter_class = ContentFilter


class ArtifactViewSet(NamedModelViewSet):
    endpoint_name = 'artifacts'
    queryset = Artifact.objects.all()
    serializer_class = ArtifactSerializer
    filter_class = ArtifactFilter

    def update(self, request, pk):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
