from gettext import gettext as _
import itertools

from django_filters.rest_framework import filters, filterset
from django_filters import Filter
from rest_framework import decorators, mixins, serializers

from pulpcore.app import tasks
from pulpcore.app.models import (
    Content,
    Distribution,
    Exporter,
    Remote,
    Publication,
    Publisher,
    Repository,
    RepositoryContent,
    RepositoryVersion
)
from pulpcore.app.pagination import UUIDPagination, NamePagination
from pulpcore.app.response import OperationPostponedResponse
from pulpcore.app.serializers import (
    ContentSerializer,
    DistributionSerializer,
    ExporterSerializer,
    RemoteSerializer,
    PublicationSerializer,
    PublisherSerializer,
    RepositorySerializer,
    RepositoryVersionSerializer
)
from pulpcore.app.viewsets import NamedModelViewSet, AsyncUpdateMixin, AsyncRemoveMixin
from pulpcore.app.viewsets.base import NAME_FILTER_OPTIONS, DATETIME_FILTER_OPTIONS


class RepositoryFilter(filterset.FilterSet):
    name = filters.CharFilter()

    class Meta:
        model = Repository
        fields = {'name': NAME_FILTER_OPTIONS}


class RepositoryViewSet(NamedModelViewSet,
                        mixins.CreateModelMixin,
                        mixins.UpdateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        mixins.DestroyModelMixin):
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
            [instance],
            args=(instance.id, ),
            kwargs={'data': request.data, 'partial': partial}
        )
        return OperationPostponedResponse(async_result, request)

    def destroy(self, request, pk):
        """
        Generates a Task to delete a Repository
        """
        repo = self.get_object()
        async_result = tasks.repository.delete.apply_async_with_reservation(
            [repo], kwargs={'repo_id': repo.id})
        return OperationPostponedResponse(async_result, request)


class RepositoryVersionContentFilter(Filter):
    """
    Filter used to get the repository versions where some given content can be found.

    Given a content_href, this filter will:
        1. Get the RepositoryContent that the content can be found in
        2. Get a list of version_added and version_removed where the content was
           changed on the repository
        3. Calculate and return the versions that the content can be found on
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', _('Content Unit referenced by HREF'))
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        """
        Args:
            qs (django.db.models.query.QuerySet): The RepositoryVersion Queryset
            value (string): of content href to filter

        Returns:
            Queryset of the RepositoryVersions containing the specified content
        """

        if not value:
            raise serializers.ValidationError(detail=_('No value supplied for content filter'))

        # Get the content object from the content_href
        content = NamedModelViewSet.get_resource(value, Content)

        # Get the repository from the parent request.
        repository_pk = self.parent.request.parser_context['kwargs']['repository_pk']
        repository = Repository.objects.get(pk=repository_pk)

        repository_content_set = RepositoryContent.objects.filter(content=content,
                                                                  repository=repository)

        # Get the sorted list of version_added and version_removed.
        version_added = list(repository_content_set.values_list('version_added__number', flat=True))

        # None values have to be filtered out from version_removed,
        # in order for zip_longest to pass it a default fillvalue
        version_removed = list(filter(None.__ne__, repository_content_set
                                      .values_list('version_removed__number', flat=True)))

        # The range finding should work as long as both lists are sorted
        # Why it works: https://gist.github.com/werwty/6867f83ae5adbae71e452c28ecd9c444
        version_added.sort()
        version_removed.sort()

        # Match every version_added to a version_removed, if len(version_removed)
        # is shorter than len(version_added), pad out the remaining space with the current
        # repository version +1 (the +1 is to the current version gets included when we
        # calculate range)
        version_tuples = itertools.zip_longest(version_added, version_removed,
                                               fillvalue=repository.last_version + 1)

        # Get the ranges between paired version_added and version_removed to get all
        # the versions the content is present in.
        versions = [list(range(added, removed)) for (added, removed) in version_tuples]
        # Flatten the list of lists
        versions = list(itertools.chain.from_iterable(versions))

        return qs.filter(number__in=versions)


class RepositoryVersionFilter(filterset.FilterSet):
    # e.g.
    # /?number=4
    # /?number__range=4,6
    # /?created__gte=2018-04-12T19:45
    # /?created__range=2018-04-12T19:45,2018-04-13T20:00
    # /?content=http://localhost:8000/api/v3/content/file/fb8ad2d0-03a8-4e36-a209-77763d4ed16c/
    number = filters.NumberFilter()
    created = filters.IsoDateTimeFilter()
    content = RepositoryVersionContentFilter()

    class Meta:
        model = RepositoryVersion
        fields = {
            'number': ['exact', 'lt', 'lte', 'gt', 'gte', 'range'],
            'created': DATETIME_FILTER_OPTIONS,
            'content': ['exact', 'in']
        }


class RepositoryVersionViewSet(NamedModelViewSet,
                               mixins.RetrieveModelMixin,
                               mixins.ListModelMixin):
    endpoint_name = 'versions'
    nest_prefix = 'repositories'
    router_lookup = 'version'
    lookup_field = 'number'
    parent_viewset = RepositoryViewSet
    parent_lookup_kwargs = {'repository_pk': 'repository__pk'}
    serializer_class = RepositoryVersionSerializer
    queryset = RepositoryVersion.objects.exclude(complete=False)
    filter_class = RepositoryVersionFilter

    @decorators.detail_route()
    def content(self, request, repository_pk, number):
        return self._paginated_response(self.get_object().content, request)

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
            [version.repository], kwargs={'pk': version.pk}
        )
        return OperationPostponedResponse(async_result, request)

    def create(self, request, repository_pk):
        """
        Queues a task that creates a new RepositoryVersion by adding and removing content units
        """
        add_content_units = []
        remove_content_units = []
        repository = self.get_parent_object()

        if 'add_content_units' in request.data:
            for url in request.data['add_content_units']:
                content = self.get_resource(url, Content)
                add_content_units.append(content.pk)

        if 'remove_content_units' in request.data:
            for url in request.data['remove_content_units']:
                content = self.get_resource(url, Content)
                remove_content_units.append(content.pk)

        result = tasks.repository.add_and_remove.apply_async_with_reservation(
            [repository],
            kwargs={
                'repository_pk': repository_pk,
                'add_content_units': add_content_units,
                'remove_content_units': remove_content_units
            }
        )
        return OperationPostponedResponse(result, request)


class RemoteFilter(filterset.FilterSet):
    """
    Plugin remote filter should:
     - inherit from this class
     - add any specific filters if needed
     - define a `Meta` class which should:
       - specify a plugin remote model for which filter is defined
       - extend `fields` with specific ones
    """
    name = filters.CharFilter()
    last_updated = filters.IsoDateTimeFilter()

    class Meta:
        model = Remote
        fields = {
            'name': NAME_FILTER_OPTIONS,
            'last_updated': DATETIME_FILTER_OPTIONS
        }


class RemoteViewSet(NamedModelViewSet,
                    mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    AsyncUpdateMixin,
                    AsyncRemoveMixin):
    endpoint_name = 'remotes'
    serializer_class = RemoteSerializer
    queryset = Remote.objects.all()
    filter_class = RemoteFilter


class PublisherFilter(filterset.FilterSet):
    """
    Plugin publisher filter should:
     - inherit from this class
     - add any specific filters if needed
     - define a `Meta` class which should:
       - specify a plugin publisher model for which filter is defined
       - extend `fields` with specific ones
    """
    name = filters.CharFilter()
    last_updated = filters.IsoDateTimeFilter()

    class Meta:
        model = Publisher
        fields = {
            'name': NAME_FILTER_OPTIONS,
            'last_updated': DATETIME_FILTER_OPTIONS
        }


class PublisherViewSet(NamedModelViewSet,
                       mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.ListModelMixin,
                       AsyncUpdateMixin,
                       AsyncRemoveMixin):
    endpoint_name = 'publishers'
    serializer_class = PublisherSerializer
    queryset = Publisher.objects.all()
    filter_class = PublisherFilter


class ExporterFilter(filterset.FilterSet):
    """
    Plugin exporter filter should:
     - inherit from this class
     - add any specific filters if needed
     - define a `Meta` class which should:
       - specify a plugin exporter model for which filter is defined
       - extend `fields` with specific ones
    """
    name = filters.CharFilter()
    last_export = filters.IsoDateTimeFilter()

    class Meta:
        model = Exporter
        fields = {
            'name': NAME_FILTER_OPTIONS,
            'last_export': DATETIME_FILTER_OPTIONS
        }


class ExporterViewSet(NamedModelViewSet,
                      mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.ListModelMixin,
                      AsyncUpdateMixin,
                      AsyncRemoveMixin):
    endpoint_name = 'exporters'
    serializer_class = ExporterSerializer
    queryset = Exporter.objects.all()
    filter_class = ExporterFilter


class PublicationViewSet(NamedModelViewSet,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         mixins.DestroyModelMixin):
    endpoint_name = 'publications'
    queryset = Publication.objects.exclude(complete=False)
    serializer_class = PublicationSerializer


class DistributionFilter(filterset.FilterSet):
    # e.g.
    # /?name=foo
    # /?name__in=foo,bar
    # /?base_path__contains=foo
    # /?base_path__icontains=foo
    name = filters.CharFilter()
    base_path = filters.CharFilter()

    class Meta:
        model = Distribution
        fields = {
            'name': NAME_FILTER_OPTIONS,
            'base_path': ['exact', 'contains', 'icontains', 'in']
        }


class DistributionViewSet(NamedModelViewSet,
                          mixins.CreateModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.ListModelMixin,
                          mixins.DestroyModelMixin):
    endpoint_name = 'distributions'
    queryset = Distribution.objects.all()
    serializer_class = DistributionSerializer
    filter_class = DistributionFilter
