from django_filters.rest_framework import filters, filterset
from django_filters import CharFilter
from rest_framework import decorators

from pulp.app import tasks
from pulp.app.models import Importer, Publisher, Repository, RepositoryContent
from pulp.app.pagination import UUIDPagination, NamePagination
from pulp.app.response import OperationPostponedResponse
from pulp.app.serializers import (ContentSerializer, ImporterSerializer, PublisherSerializer,
                                  RepositorySerializer, RepositoryContentSerializer)
from pulp.app.viewsets import NamedModelViewSet
from pulp.app.viewsets.custom_filters import CharInFilter
from pulp.common import tags


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
    pagination_class = NamePagination
    filter_class = RepositoryFilter

    @decorators.detail_route()
    def content(self, request, name):
        repo = self.get_object()
        paginator = UUIDPagination()
        page = paginator.paginate_queryset(repo.content, request)
        serializer = ContentSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    @decorators.detail_route()
    def importers(self, request, name):
        """
        Creates a nested `importers/` endpoint that returns each importer associated with this
        repository.
        """
        repo = self.get_object()
        importers = Importer.objects.filter(repository__name=repo.name)
        paginator = UUIDPagination()
        page = paginator.paginate_queryset(importers, request)
        serializer = ImporterSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def destroy(self, request, name):
        repo = self.get_object()
        async_result = tasks.repository.delete.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo.name, kwargs={'repo_name': repo.name})
        return OperationPostponedResponse([async_result])


class ContentAdaptorFilter(filterset.FilterSet):
    """
    A base ContentAdaptor filter which cannot be used on its own.

    Importer/Publisher base filters would need:
     - to inherit from this class
     - to add any specific filters if needed
     - to define its own `Meta` class which needs:

       - to specify model for which filter is defined
       - to extend `fields` with specific ones
    """
    repo_name = CharFilter(name="repository__name")

    class Meta:
        # One should not specify ContentAdaptor model here because it is an abstract model
        # so it does not have managers which are required by filters to query data from db.
        fields = ['name', 'last_updated', 'repo_name']


class ImporterFilter(ContentAdaptorFilter):
    """
    Plugin importer filter would need:
     - to inherit from this class
     - to add any specific filters if needed
     - to define its own `Meta` class which needs:

       - to specify a plugin importer model for which filter is defined
       - to extend `fields` with specific ones
    """
    class Meta:
        model = Importer
        fields = ContentAdaptorFilter.Meta.fields


class PublisherFilter(ContentAdaptorFilter):
    """
    Plugin publisher filter would need:
     - to inherit from this class
     - to add any specific filters if needed
     - to define its own `Meta` class which needs:

       - to specify a plugin publisher model for which filter is defined
       - to extend `fields` with specific ones
    """
    class Meta:
        model = Publisher
        fields = ContentAdaptorFilter.Meta.fields


class ImporterViewSet(NamedModelViewSet):
    queryset = Importer.objects.all()
    serializer_class = ImporterSerializer
    endpoint_name = 'importers'
    filter_class = ImporterFilter

    def destroy(self, request, pk):
        importer = self.get_object()
        async_result = tasks.importer.delete.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, importer.repository.name,
            kwargs={'repo_name': importer.repository.name,
                    'importer_name': importer.name}
        )
        return OperationPostponedResponse([async_result])


class PublisherViewSet(NamedModelViewSet):
    endpoint_name = 'publishers'
    serializer_class = PublisherSerializer
    queryset = Publisher.objects.all()
    filter_class = PublisherFilter

    def destroy(self, request, pk):
        publisher = self.get_object()
        repo_name = publisher.repository.name
        task_params = {'repo_name': repo_name,
                       'publisher_name': publisher.name}
        async_result = tasks.publisher.delete.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_name, **task_params)

        return OperationPostponedResponse([async_result])


class RepositoryContentViewSet(NamedModelViewSet):
    endpoint_name = 'repositorycontents'
    queryset = RepositoryContent.objects.all()
    serializer_class = RepositoryContentSerializer
