from django_filters.rest_framework import filterset

from pulpcore.app.models import User
from pulpcore.app.serializers import UserSerializer
from pulpcore.app.viewsets import NamedModelViewSet
from pulpcore.app.viewsets.custom_filters import CharInFilter


class UserFilter(filterset.FilterSet):
    username_in_list = CharInFilter(name='username', lookup_expr='in')

    class Meta:
        model = User
        fields = ['username', 'username_in_list']


class UserViewSet(NamedModelViewSet):
    endpoint_name = 'users'
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_class = UserFilter
