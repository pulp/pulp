from django_filters.rest_framework import filterset

from pulpcore.app.models import Task, Worker
from pulpcore.app.serializers import TaskSerializer, WorkerSerializer
from pulpcore.app.viewsets import NamedModelViewSet
from pulpcore.app.viewsets.base import GenericNamedModelViewSet
from pulpcore.tasking.util import cancel as cancel_task

from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework import status, mixins


class TaskFilter(filterset.FilterSet):

    class Meta:
        model = Task
        fields = ['state', 'worker__name']


class TaskViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  GenericNamedModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    endpoint_name = 'tasks'
    filter_class = TaskFilter

    @detail_route(methods=('post',))
    def cancel(self, request, pk=None):
        task = self.get_object()
        cancel_task(task.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkerViewSet(NamedModelViewSet):
    queryset = Worker.objects.all()
    serializer_class = WorkerSerializer
    endpoint_name = 'workers'
    http_method_names = ['get', 'options']
    lookup_value_regex = '[^/]+'
