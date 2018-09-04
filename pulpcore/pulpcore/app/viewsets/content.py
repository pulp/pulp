from gettext import gettext as _
from collections import OrderedDict

from django.db import models, transaction
from drf_yasg import openapi
from drf_yasg.inspectors.view import SwaggerAutoSchema
from drf_yasg.utils import guess_response_status, is_list_view
from rest_framework import status, mixins
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from pulpcore.app.models import Artifact, Content, ContentArtifact
from pulpcore.app.serializers import ArtifactSerializer, ContentSerializer
from pulpcore.app.viewsets import BaseFilterSet, NamedModelViewSet


class ArtifactSchema(SwaggerAutoSchema):
    """This schema inspector is to be used for the ArtifactViewset.

    The default behavior of SwaggerAutoSchema skips generating a response schema if the update
    operation requires a multipart form upload. This view inspector generates a response anyway.

    """
    def get_default_responses(self):
        """Get the default responses determined for this view from the request serializer and
        request method.

        :type: dict[str, openapi.Schema]
        """
        method = self.method.lower()

        default_status = guess_response_status(method)
        default_schema = ''
        if method in ('get', 'post', 'put', 'patch'):
            default_schema = self.get_default_response_serializer()

        default_schema = default_schema or ''

        if default_schema and not isinstance(default_schema, openapi.Schema):
            default_schema = self.serializer_to_schema(default_schema) or ''

        if default_schema:
            if is_list_view(self.path, self.method, self.view) and self.method.lower() == 'get':
                default_schema = openapi.Schema(type=openapi.TYPE_ARRAY, items=default_schema)
            if self.should_page():
                default_schema = self.get_paginated_response(default_schema) or default_schema

        return OrderedDict({str(default_status): default_schema})


class ArtifactFilter(BaseFilterSet):
    """
    Artifact filter Plugin content filters should:
     - inherit from this class
     - add any plugin-specific filters if needed
     - define its own `Meta` class should:
       - specify plugin content model
       - extend `fields` with plugin-specific ones
    """
    class Meta:
        model = Artifact
        fields = ['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512']


class ArtifactViewSet(NamedModelViewSet,
                      mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.ListModelMixin,
                      mixins.DestroyModelMixin):
    endpoint_name = 'artifacts'
    queryset = Artifact.objects.all()
    serializer_class = ArtifactSerializer
    filterset_class = ArtifactFilter
    parser_classes = (MultiPartParser, FormParser)
    swagger_schema = ArtifactSchema

    def destroy(self, request, pk):
        """
        Remove Artifact only if it is not associated with any Content.
        """
        try:
            return super().destroy(request, pk)
        except models.ProtectedError:
            msg = _('The Artifact cannot be deleted because it is associated with Content.')
            data = {'detail': msg}
            return Response(data, status=status.HTTP_409_CONFLICT)


class ContentFilter(BaseFilterSet):
    """
    Plugin content filters should:
     - inherit from this class
     - add any plugin-specific filters if needed
     - define its own `Meta` class which should:
       - specify plugin content model
       - extend `fields` with plugin-specific ones
    """
    class Meta:
        model = Content
        fields = {'type': ['exact', 'in']}


class ContentViewSet(NamedModelViewSet,
                     mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.ListModelMixin):
    endpoint_name = 'content'
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    filterset_class = ContentFilter

    @transaction.atomic
    def create(self, request):
        """
        Create a Content Artifact
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        artifacts = serializer.validated_data.pop('artifacts')
        content = serializer.save()

        for relative_path, artifact in artifacts.items():
            ca = ContentArtifact(artifact=artifact, content=content, relative_path=relative_path)
            ca.save()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
