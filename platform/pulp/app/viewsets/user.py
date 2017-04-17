from pulp.app.models import User
from pulp.app.serializers import UserSerializer
from pulp.app.viewsets import NamedModelViewSet


class UserViewSet(NamedModelViewSet):
    endpoint_name = 'users'
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'username'
