from django_filters.rest_framework import filters, filterset
from django_filters import CharFilter
from rest_framework import decorators, mixins

from pulpcore.app import tasks
from pulpcore.app.models import (Distribution,
                                 Importer,
                                 Publication,
                                 Publisher,
                                 Repository,
                                 RepositoryVersion)
from pulpcore.app.pagination import UUIDPagination, NamePagination
from pulpcore.app.response import OperationPostponedResponse
from pulpcore.app.serializers import (ContentSerializer,
                                      DistributionSerializer,
                                      ImporterSerializer,
                                      PublicationSerializer,
                                      PublisherSerializer,
                                      RepositorySerializer,
                                      RepositoryVersionSerializer)
from pulpcore.app.viewsets import (NamedModelViewSet,
                                   GenericNamedModelViewSet,
                                   CreateReadAsyncUpdateDestroyNamedModelViewset)
from pulpcore.app.viewsets.custom_filters import CharInFilter
from pulpcore.common import tags


class RepositoryFilter(filterset.FilterSet):
    name_in_list = CharInFilter(name='name', lookup_expr='in')
    content_added_since = filters.Filter(name='last_content_added', lookup_expr='gt')

    class Meta:
        model = Repository
        fields = ['name', 'name_in_list', 'content_added_since']


class RepositoryViewSet(NamedModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    endpoint_name = 'repositories'
    router_lookup = 'repository'
    pagination_class = NamePagination
    filter_class = RepositoryFilter

    def update(self, request, pk, partial=False):
        """
        Generates a Task to update a Repository
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

    def destroy(self, request, pk):
        """
        Generates a Task to delete a Repository
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
    name_in_list = CharInFilter(name='name', lookup_expr='in')

    class Meta:
        model = Importer
        fields = ContentAdaptorFilter.Meta.fields + ['name_in_list']


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


class RepositoryVersionViewSet(GenericNamedModelViewSet,
                               mixins.RetrieveModelMixin,
                               mixins.ListModelMixin,
                               mixins.DestroyModelMixin):
    endpoint_name = 'versions'
    nest_prefix = 'repositories'
    router_lookup = 'version'
    lookup_field = 'number'
    parent_viewset = RepositoryViewSet
    parent_lookup_kwargs = {'repository_pk': 'repository__pk'}
    serializer_class = RepositoryVersionSerializer
    queryset = RepositoryVersion.objects.exclude(complete=False)

    @decorators.detail_route()
    def content(self, request, repository_pk, number):
        return self._paginated_response(self.get_object().content(), request)

    @decorators.detail_route()
    def added_content(self, request, repository_pk, number):
        """
        Display content added since the previous Repository Version.
        """
        return self._paginated_response(self.get_object().added(), request)

    @decorators.detail_route()
    def removed_content(self, request, repository_pk, number):
        """
        Display content removed since the previous Repository Version.
        """
        return self._paginated_response(self.get_object().removed(), request)

    def _paginated_response(self, content, request):
        """
        a helper method to make a paginated response for content list views.

        Args:
            content (django.db.models.QuerySet): the Content to render
            request (rest_framework.request.Request): the current HTTP request being handled

        Returns:
            rest_framework.response.Response: a paginated response for the corresponding content
        """
        paginator = UUIDPagination()
        page = paginator.paginate_queryset(content, request)
        serializer = ContentSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def destroy(self, request, repository_pk, number):
        """
        Queues a task to handle deletion of a RepositoryVersion
        """
        version = self.get_object()
        async_result = tasks.repository.delete_version.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repository_pk,
            kwargs={'pk': version.pk}
        )
        return OperationPostponedResponse([async_result], request)


class ImporterViewSet(CreateReadAsyncUpdateDestroyNamedModelViewset):
    endpoint_name = 'importers'
    serializer_class = ImporterSerializer
    queryset = Importer.objects.all()
    filter_class = ImporterFilter


class PublisherViewSet(CreateReadAsyncUpdateDestroyNamedModelViewset):
    endpoint_name = 'publishers'
    serializer_class = PublisherSerializer
    queryset = Publisher.objects.all()
    filter_class = PublisherFilter


class PublicationViewSet(NamedModelViewSet):
    endpoint_name = 'publications'
    queryset = Publication.objects.all()
    serializer_class = PublicationSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        publisher = serializer.validated_data.pop('publisher')
        result = tasks.publisher.publish.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, str(publisher.repository.pk),
            kwargs={
                'publisher_pk': publisher.pk,
            }
        )
        return OperationPostponedResponse([result], request)


class DistributionViewSet(NamedModelViewSet):
    endpoint_name = 'distributions'
    queryset = Distribution.objects.all()
    serializer_class = DistributionSerializer
