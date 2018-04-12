from django_filters.rest_framework import filters, filterset
from rest_framework import mixins

from pulpcore.app.models import User
from pulpcore.app.serializers import UserSerializer
from pulpcore.app.viewsets import NamedModelViewSet
from pulpcore.app.viewsets.base import NAME_FILTER_OPTIONS


class UserFilter(filterset.FilterSet):
    username = filters.CharFilter()

    class Meta:
        model = User
        fields = {'username': NAME_FILTER_OPTIONS}


class UserViewSet(NamedModelViewSet,
                  mixins.CreateModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  mixins.DestroyModelMixin):
    endpoint_name = 'users'
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_class = UserFilter
