from pulpcore.app.models import User
from pulpcore.app.serializers import UserSerializer
from pulpcore.app.viewsets import NamedModelViewSet


class UserViewSet(NamedModelViewSet):
    endpoint_name = 'users'
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'username'
