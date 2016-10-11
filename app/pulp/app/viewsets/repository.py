import django_filters
from rest_framework import decorators, filters, pagination


from pulp.app.models import Repository
from pulp.app.pagination import UUIDPagination
from pulp.app.serializers import ContentSerializer, RepositorySerializer
from pulp.app.viewsets import NamedModelViewSet
from pulp.app.viewsets.custom_filters import CharInFilter


class RepositoryPagination(pagination.CursorPagination):
    """
    Repository paginator, orders repositories by name when paginating.
    """
    ordering = 'name'


class RepositoryFilter(filters.FilterSet):
    """
    Available Filters:

        `name`: Filter by Repository name
                Use: name=<repo_a>

        `name_in_list`: Filter by multiple Repository names
                        Use: name_in_list=<repo_a>,<repo_b>

        `content_added_since`: Filter for repositories with content added after given date or
                               datetime
                               Use: content_added_since=2015-10-11T17:15:41.557494Z
                               Use: content_added_since=2015-10-11

    """
    name_in_list = CharInFilter(name='name', lookup_expr='in')
    content_added_since = django_filters.Filter(name='last_content_added', lookup_expr='gt')

    class Meta:
        model = Repository
        fields = ['name', 'name_in_list', 'content_added_since']


class RepositoryViewSet(NamedModelViewSet):
    """
    This endpoint presents repositories.
    """
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
