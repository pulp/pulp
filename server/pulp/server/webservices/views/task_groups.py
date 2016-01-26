"""
This module contains views related to Pulp's task groups.
"""
from django.views.generic import View

from pulp.common.constants import CALL_STATES
from pulp.server.auth import authorization
from pulp.server.db.model import TaskStatus
from pulp.server.exceptions import MissingResource
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.util import generate_json_response_with_pulp_encoder


class TaskGroupView(View):
    """
    View for a task group.
    """

    @auth_required(authorization.READ)
    def get(self, request, group_id):
        """
        Return a response containing a list of tasks for task group.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param group_id: The ID of the task group you wish to summarize
        :type  group_id: basestring

        :return: Response containing a list of the tasks in task group
        :rtype : django.http.HttpResponse
        :raises MissingResource: if group id is not found
        """
        raise MissingResource(group_id)


class TaskGroupSummaryView(View):
    """
    View for a task group summary.
    """

    @auth_required(authorization.READ)
    def get(self, request, group_id):
        """
        Return a response containing a summary of task states for task group.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param group_id: The ID of the task group you wish to summarize
        :type  group_id: basestring

        :return: Response containing a serialized dict of the task group summary
        :rtype : django.http.HttpResponse
        """
        tasks = TaskStatus.objects(group_id=group_id)
        task_group_total = tasks.count()

        summary = {'total': task_group_total}
        for state in CALL_STATES:
            summary[state] = tasks.filter(state=state).count()

        return generate_json_response_with_pulp_encoder(summary)
