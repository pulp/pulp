from django_filters.rest_framework import filters, filterset
from django_filters import CharFilter
from rest_framework import decorators

from pulpcore.app import tasks
from pulpcore.app.models import Importer, Publisher, Repository, RepositoryContent
from pulpcore.app.pagination import UUIDPagination, NamePagination
from pulpcore.app.response import OperationPostponedResponse
from pulpcore.app.serializers import (ContentSerializer, ImporterSerializer, PublisherSerializer,
                                  RepositorySerializer, RepositoryContentSerializer)
from pulpcore.app.viewsets import NamedModelViewSet
from pulpcore.app.viewsets.custom_filters import CharInFilter
from pulpcore.common import tags


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

    def update(self, request, name, partial=False):
        """
        Generates a Task to update a :class:`~pulpcore.app.models.Repository`
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        async_result = tasks.repository.update.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, str(instance.id),
            args=(instance.id, ),
            kwargs={'data': request.data,
                    'partial': partial}
        )
        return OperationPostponedResponse([async_result], request)

    def destroy(self, request, name):
        """
        Generates a Task to delete a :class:`~pulpcore.app.models.Repository`
        """
        repo = self.get_object()
        async_result = tasks.repository.delete.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, str(repo.id), kwargs={'repo_id': repo.id})
        return OperationPostponedResponse([async_result], request)


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

    def update(self, request, pk, partial=False):
        importer = self.get_object()
        serializer = self.get_serializer(importer, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        app_label = importer._meta.app_label
        async_result = tasks.importer.update.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, importer.repository.name,
            args=(importer.id, app_label, serializer.__class__.__name__),
            kwargs={'data': request.data, 'partial': partial}
        )
        return OperationPostponedResponse([async_result], request)

    def destroy(self, request, pk):
        importer = self.get_object()
        async_result = tasks.importer.delete.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, importer.repository.name,
            kwargs={'repo_name': importer.repository.name,
                    'importer_name': importer.name}
        )
        return OperationPostponedResponse([async_result], request)

    @decorators.detail_route()
    def sync(self, request, pk):
        importer = self.get_object()
        async_result = tasks.importer.sync.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, importer.repository.name,
            kwargs={'repo_name': importer.repository.name,
                    'importer_name': importer.name}
        )
        return OperationPostponedResponse([async_result], request)


class PublisherViewSet(NamedModelViewSet):
    endpoint_name = 'publishers'
    serializer_class = PublisherSerializer
    queryset = Publisher.objects.all()
    filter_class = PublisherFilter

    def update(self, request, pk, partial=False):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        app_label = instance._meta.app_label
        async_result = tasks.publisher.update.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, instance.repository.name,
            args=(instance.id, app_label, serializer.__class__.__name__),
            kwargs={'data': request.data, 'partial': partial}
        )
        return OperationPostponedResponse([async_result], request)

    def destroy(self, request, pk):
        publisher = self.get_object()
        repo_name = publisher.repository.name
        task_params = {'repo_name': repo_name,
                       'publisher_name': publisher.name}
        async_result = tasks.publisher.delete.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_name, **task_params)

        return OperationPostponedResponse([async_result], request)

    @decorators.detail_route()
    def publish(self, request, pk):
        publisher = self.get_object()
        async_result = tasks.publisher.publish.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, publisher.repository.name,
            kwargs={'repo_name': publisher.repository.name,
                    'publisher_name': publisher.name}
        )
        return OperationPostponedResponse([async_result], request)


class RepositoryContentViewSet(NamedModelViewSet):
    endpoint_name = 'repositorycontents'
    queryset = RepositoryContent.objects.all()
    serializer_class = RepositoryContentSerializer
