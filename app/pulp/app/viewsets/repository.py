from django_filters.rest_framework import filters, filterset
from rest_framework import decorators, pagination

from pulp.app.models import Importer, Publisher, Repository
from pulp.app.pagination import UUIDPagination
from pulp.app.serializers import (ContentSerializer, ImporterSerializer, PublisherSerializer,
                                  RepositorySerializer)
from pulp.app.viewsets import NamedModelViewSet
from pulp.app.viewsets.custom_filters import CharInFilter


class RepositoryPagination(pagination.CursorPagination):
    """
    Repository paginator, orders repositories by name when paginating.
    """
    ordering = 'name'


class RepositoryFilter(filterset.FilterSet):
    name_in_list = CharInFilter(name='name', lookup_expr='in')
    content_added_since = filters.Filter(name='last_content_added', lookup_expr='gt')

    class Meta:
        model = Repository
        fields = ['name', 'name_in_list', 'content_added_since']


class RepositoryViewSet(NamedModelViewSet):
    lookup_field = 'name'
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    endpoint_name = 'repositories'
    pagination_class = RepositoryPagination
    filter_class = RepositoryFilter

    @decorators.detail_route()
    def content(self, request, name):
        # XXX Not sure if we actually want to put a content view on repos like this, this is
        #     just an example of how you might include a related queryset, and in a paginated way.
        repo = self.get_object()
        paginator = UUIDPagination()
        page = paginator.paginate_queryset(repo.content, request)
        serializer = ContentSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    @decorators.detail_route()
    def importers(self, request, name):
        # Creates a repositories/<repo>/importers/ endpoint.
        # This will link to all importers that are associated within the repository.
        repo = self.get_object()
        importers = Importer.objects.filter(repository__name=repo.name)
        paginator = UUIDPagination()
        page = paginator.paginate_queryset(importers, request)
        serializer = ImporterSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class ImporterViewSet(NamedModelViewSet):
    # Indicates that importer urls should be routed through their associated repository.
    nested_parent = RepositoryViewSet
    # Name the parameter to generate the link. This is important because `name` in this url refers
    # to `Importer.name`, not `Repository.name`
    nested_parent_lookup_name = 'repo_name'
    endpoint_name = 'importers'
    serializer_class = ImporterSerializer
    queryset = Importer.objects.all()


class PublisherViewSet(NamedModelViewSet):
    endpoint_name = 'publishers'
    serializer_class = PublisherSerializer
    queryset = Publisher.objects.all()
