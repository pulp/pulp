from rest_framework import decorators
from rest_framework.response import Response

from pulpcore.app.models import User
from pulpcore.app.serializers import UserSerializer
from pulpcore.app.viewsets import NamedModelViewSet


class UserViewSet(NamedModelViewSet):
    endpoint_name = 'users'
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'username'

    @decorators.detail_route(methods=('post',))
    def jwt_reset(self, request, username):
        user = self.get_object()
        user.jwt_reset()
        serializer = self.get_serializer(user)
        return Response(serializer.data)
