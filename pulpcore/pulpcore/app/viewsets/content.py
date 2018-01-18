from gettext import gettext as _

from django.db import models, transaction
from django_filters.rest_framework import filterset
from rest_framework import status
from rest_framework.response import Response


from pulpcore.app.models import Artifact, Content, ContentArtifact
from pulpcore.app.serializers import ArtifactSerializer, ContentSerializer
from pulpcore.app.viewsets import CreateDestroyReadNamedModelViewSet


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


class ContentViewSet(CreateDestroyReadNamedModelViewSet):
    endpoint_name = 'content'
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    filter_class = ContentFilter

    @transaction.atomic
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        artifacts = serializer.validated_data.pop('artifacts')
        content = serializer.save()

        for relative_path, artifact in artifacts.items():
            ca = ContentArtifact(artifact=artifact, content=content, relative_path=relative_path)
            ca.save()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ArtifactViewSet(CreateDestroyReadNamedModelViewSet):
    endpoint_name = 'artifacts'
    queryset = Artifact.objects.all()
    serializer_class = ArtifactSerializer
    filter_class = ArtifactFilter

    def destroy(self, request, pk):
        """
        Remove Artifact only if it is not associated with any Content.
        """
        try:
            return super(ArtifactViewSet, self).destroy(request, pk)
        except models.ProtectedError:
            msg = _('The Artifact cannot be deleted because it is associated with Content.')
            data = {'detail': msg}
            return Response(data, status=status.HTTP_409_CONFLICT)
