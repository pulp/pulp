from django_filters.rest_framework import filters, filterset

from pulpcore.app.models import Task, Worker
from pulpcore.app.models.task import CoreUpdateTask, CoreDeleteTask
from pulpcore.app.serializers import TaskSerializer, WorkerSerializer
from pulpcore.app.serializers.task import CoreUpdateTaskSerializer
from pulpcore.app.viewsets import NamedModelViewSet
from pulpcore.app.viewsets.base import GenericNamedModelViewSet
from pulpcore.app.viewsets.custom_filters import CharInFilter, HyperlinkRelatedFilter
from pulpcore.tasking.util import cancel as cancel_task

from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework import status, mixins


class TaskFilter(filterset.FilterSet):
    state_in_list = CharInFilter(name='state', lookup_expr='in')
    worker = HyperlinkRelatedFilter(name='worker')

    started_after = filters.DateTimeFilter(name='started_at', lookup_expr='gte')
    started_before = filters.DateTimeFilter(name='started_at', lookup_expr='lte')

    finished_after = filters.DateTimeFilter(name='finished_at', lookup_expr='gte')
    finished_before = filters.DateTimeFilter(name='finished_at', lookup_expr='lte')

    class Meta:
        model = Task
        fields = ['state', 'state_in_list', 'worker', 'started_after', 'started_before',
                  'finished_after', 'finished_before']


class TaskViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  GenericNamedModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    endpoint_name = 'tasks'
    filter_class = TaskFilter

    # TODO(asmacdo) does this work?
    @detail_route(methods=('post',))
    def cancel(self, request, pk=None):
        task = self.get_object()
        cancel_task(task.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CoreUpdateTaskViewSet(TaskViewSet):

    endpoint_name = 'core/updates'
    queryset = CoreUpdateTask.objects.all()
    model = CoreUpdateTask
    serializer_class = CoreUpdateTaskSerializer


class CoreDeleteTaskViewSet(TaskViewSet):

    endpoint_name = 'core/deletes'
    queryset = CoreDeleteTask.objects.all()
    model = CoreDeleteTask
    serializer_class = CoreUpdateTaskSerializer


class WorkerViewSet(NamedModelViewSet):
    queryset = Worker.objects.all()
    serializer_class = WorkerSerializer
    endpoint_name = 'workers'
    http_method_names = ['get', 'options']
    lookup_value_regex = '[^/]+'
