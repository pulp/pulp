from pulp.app.models import Content
from pulp.app.serializers import ContentSerializer
from pulp.app.viewsets import NamedModelViewSet


class ContentViewSet(NamedModelViewSet):
    endpoint_name = 'content'
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
