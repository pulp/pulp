from datetime import datetime

from django.views.generic import View
from mongoengine.queryset import DoesNotExist

from pulp.server.async import tasks
from pulp.server.auth import authorization
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.exceptions import MissingResource
from pulp.server.db.model.resources import Worker
from pulp.server.managers import factory
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder)


def task_serializer(task):
    """
    Update the task representation in the database to match the model for the API

    :param task: The task from the database
    :type task: dict
    :return: the same task modified for use by the API
    :rtype: dict
    """
    task = serialization.dispatch.task_status(task)
    task.update(serialization.dispatch.spawned_tasks(task))
    task.update(serialization.dispatch.task_result_href(task))
    return task


class TaskCollectionView(View):
    """
    View for all tasks.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        Return a response containing a list of all tasks.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a serialized list of dicts, one for each task
        :rtype:  django.http.HttpResponse
        """
        tags = request.body_as_json.get('tag', [])
        if tags:
            raw_tasks = TaskStatus.objects(tags__all=tags)
        else:
            raw_tasks = TaskStatus.objects()
        serialized_task_statuses = [task_serializer(task) for task in raw_tasks]
        return generate_json_response_with_pulp_encoder(serialized_task_statuses)


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

        :return: Response containing a serialized dict of the requested task
        :rtype:  django.http.HttpResponse
        """
        try:
            task = TaskStatus.objects.get(task_id=task_id)
        except DoesNotExist:
            raise MissingResource(task_id)

        task_dict = task_serializer(task)
        if 'worker_name' in task_dict:
            queue_name = Worker(task_dict['worker_name'], datetime.now()).queue_name
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
