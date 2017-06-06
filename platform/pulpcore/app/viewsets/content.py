from django_filters.rest_framework import filterset

from pulpcore.app.models import Content
from pulpcore.app.serializers import ContentSerializer
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


class ContentViewSet(NamedModelViewSet):
    endpoint_name = 'content'
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    filter_class = ContentFilter
