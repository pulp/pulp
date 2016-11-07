from pulp.app.models import PulpUser
from pulp.app.serializers import UserSerializer
from pulp.app.viewsets import NamedModelViewSet


class UserViewSet(NamedModelViewSet):
    endpoint_name = 'users'
    queryset = PulpUser.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'username'
