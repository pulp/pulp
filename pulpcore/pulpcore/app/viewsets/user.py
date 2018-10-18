from django.contrib.auth import get_user_model
from django_filters.rest_framework import filters
from rest_framework import mixins

from pulpcore.app.serializers import UserSerializer
from pulpcore.app.viewsets import NamedModelViewSet, BaseFilterSet
from pulpcore.app.viewsets.base import NAME_FILTER_OPTIONS


User = get_user_model()


class UserFilter(BaseFilterSet):
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
    filterset_class = UserFilter
