from django_filters.rest_framework import filters, filterset
from rest_framework import status, mixins
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from pulpcore.app.models import Task, Worker
from pulpcore.app.serializers import TaskSerializer, WorkerSerializer
from pulpcore.app.viewsets.base import NamedModelViewSet
from pulpcore.app.viewsets.custom_filters import CharInFilter, HyperlinkRelatedFilter
from pulpcore.tasking.util import cancel as cancel_task


class TaskFilter(filterset.FilterSet):
    state_in_list = CharInFilter(name='state', lookup_expr='in')
    worker = HyperlinkRelatedFilter(name='worker')


    started_at = filters.IsoDateTimeFilter(name='started_at')
    finished_at = filters.IsoDateTimeFilter(name='finished_at')

    class Meta:
        model = Task
        fields = ('state', 'state_in_list', 'worker', 'started_at', 'finished_at')


class TaskViewSet(NamedModelViewSet,
                  mixins.RetrieveModelMixin,
                  mixins.ListModelMixin):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    endpoint_name = 'tasks'
    filter_class = TaskFilter

    @detail_route(methods=('post',))
    def cancel(self, request, pk=None):
        task = self.get_object()
        cancel_task(task.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkerFilter(filterset.FilterSet):
    name = filters.CharFilter()
    last_heartbeat = filters.IsoDateTimeFilter()
    online = filters.BooleanFilter(method='filter_online')
    missing = filters.BooleanFilter(method='filter_missing')

    class Meta:
        model = Worker
        fields = {
            'name': ('exact', 'startswith', 'endswith', 'contains'),
            'last_heartbeat': ('gte', 'lte'),
            'online': ('exact'),
            'missing': ('exact')
        }

    def filter_online(self, queryset, name, value):
        online_workers = Worker.objects.online_workers()

        if value:
            return online_workers
        else:
            return queryset.difference(online_workers)

    def filter_missing(self, queryset, name, value):
        missing_workers = Worker.objects.missing_workers()

        if value:
            return missing_workers
        else:
            return queryset.difference(missing_workers)


class WorkerViewSet(NamedModelViewSet,
                    mixins.RetrieveModelMixin,
                    mixins.ListModelMixin):
    queryset = Worker.objects.all()
    serializer_class = WorkerSerializer
    endpoint_name = 'workers'
    http_method_names = ['get', 'options']
    lookup_value_regex = '[^/]+'
    filter_class = WorkerFilter
