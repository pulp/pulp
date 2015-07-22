"""
This module contains views related to Pulp's task system models.
"""
from datetime import datetime

from django.views.generic import View
from django.http import HttpResponse
from mongoengine.queryset import DoesNotExist

from pulp.common import error_codes
from pulp.common.constants import CALL_CANCELED_STATE, CALL_COMPLETE_STATES
from pulp.server import exceptions as pulp_exceptions
from pulp.server.async import tasks
from pulp.server.auth import authorization
from pulp.server.db.model import Worker, TaskStatus
from pulp.server.exceptions import MissingResource
from pulp.server.webservices.views import search
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.serializers import dispatch as serial_dispatch
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder)


# This constant set is used for deleting the completed tasks from the collection.
VALID_STATES = set(filter(lambda state: state != CALL_CANCELED_STATE, CALL_COMPLETE_STATES))


def task_serializer(task):
    """
    Update the task representation in the database to match the model for the API

    :param task: The task from the database
    :type  task: dict

    :return: the same task modified for use by the API
    :rtype: dict
    """
    task = serial_dispatch.task_status(task)
    task.update(serial_dispatch.spawned_tasks(task))
    task.update(serial_dispatch.task_result_href(task))
    return task


class TaskSearchView(search.SearchView):
    """
    This view provides GET and POST searching on TaskStatus objects.
    """
    response_builder = staticmethod(generate_json_response_with_pulp_encoder)
    model = TaskStatus
    serializer = staticmethod(task_serializer)


class TaskCollectionView(View):
    """
    View for all tasks.
    """
    @auth_required(authorization.READ)
    def get(self, request):
        """
        Return a response containing a list of all tasks or a response containing
        a list of tasks filtered by the optional GET parameter 'tags'.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a serialized list of dicts, one for each task
        :rtype:  django.http.HttpResponse
        """
        tags = request.GET.getlist('tag')
        if tags:
            raw_tasks = TaskStatus.objects(tags__all=tags)
        else:
            raw_tasks = TaskStatus.objects()
        serialized_task_statuses = [task_serializer(task) for task in raw_tasks]
        return generate_json_response_with_pulp_encoder(serialized_task_statuses)

    @auth_required(authorization.DELETE)
    def delete(self, request):
        """
        Delete the tasks with status as finished, error, timed-out and skipped

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing None or pulp Exception
        :rtype:  django.http.HttpResponse or pulp.Exception
        """
        task_state = request.GET.getlist('state')
        if not task_state:
            raise pulp_exceptions.PulpCodedForbiddenException(error_code=error_codes.PLP1012)

        for state in task_state:
            if state not in VALID_STATES:
                raise pulp_exceptions.PulpCodedValidationException(
                    error_code=error_codes.PLP1011, state=state)

        for state in task_state:
                TaskStatus.objects(state=state).delete()

        return HttpResponse(status=204)


class TaskResourceView(View):
    """
    View for a single task.
    """

    @auth_required(authorization.READ)
    def get(self, request, task_id):
        """
        Return a response containing a single task.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param task_id: The ID of the task you wish to cancel
        :type  task_id: basestring

        :return: Response containing a serialized dict of the requested task
        :rtype : django.http.HttpResponse
        :raises MissingResource: if task is not found
        """
        try:
            task = TaskStatus.objects.get(task_id=task_id)
        except DoesNotExist:
            raise MissingResource(task_id)

        task_dict = task_serializer(task)
        if 'worker_name' in task_dict:
            queue_name = Worker(name=task_dict['worker_name'],
                                last_heartbeat=datetime.now()).queue_name
            task_dict.update({'queue': queue_name})
        return generate_json_response_with_pulp_encoder(task_dict)

    @auth_required(authorization.DELETE)
    def delete(self, request, task_id):
        """
        Dispatch tasks.cancel to delete a single task.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param task_id: The ID of the task you wish to cancel
        :type  task_id: basestring

        :return: Response containing None
        :rtype:  django.http.HttpResponse
        """
        tasks.cancel(task_id)
        return generate_json_response(None)
