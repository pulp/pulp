from datetime import datetime

import web

from pulp.server.async import tasks
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.auth.authorization import READ, DELETE
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.db.model.resources import Worker
from pulp.server.exceptions import MissingResource
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController


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


class SearchTaskCollection(SearchController):
    """
    Allows authorized API users to search our Task collection.
    """
    def __init__(self):
        super(SearchTaskCollection, self).__init__(TaskStatus.objects.find_by_criteria)

    @auth_required(READ)
    def GET(self):
        """
        Searches based on a Criteria object. Pass in each Criteria field as a
        query parameter.  For the 'fields' parameter, pass multiple fields as
        separate key-value pairs as is normal with query parameters in URLs. For
        example, '/v2/sometype/search/?field=id&field=display_name' will
        return the fields 'id' and 'display_name'.

        :return: json encoded response
        :rtype: str
        """
        raw_tasks = self._get_query_results_from_get()
        serialized_tasks = [task_serializer(task) for task in raw_tasks]
        return self.ok(serialized_tasks)

    @auth_required(READ)
    def POST(self):
        """
        Searches based on a Criteria object. Requires a posted parameter
        'criteria' which has a data structure that can be turned into a
        Criteria instance.

        :return: response for web browser
        :rtype: str
        """
        raw_tasks = self._get_query_results_from_post()
        serialized_tasks = [task_serializer(task) for task in raw_tasks]
        return self.ok(serialized_tasks)


class TaskCollection(JSONController):

    @auth_required(READ)
    def GET(self):
        valid_filters = ['tag']
        filters = self.filters(valid_filters)
        criteria_filters = {}
        tags = filters.get('tag', [])
        if tags:
            criteria_filters['tags'] = {'$all':  filters.get('tag', [])}
        criteria = Criteria.from_client_input({'filters': criteria_filters})
        raw_tasks = TaskStatus.objects.find_by_criteria(criteria)
        serialized_task_statuses = [task_serializer(task) for task in raw_tasks]
        return self.ok(serialized_task_statuses)


class TaskResource(JSONController):

    @auth_required(READ)
    def GET(self, task_id):
        task = TaskStatus.objects(task_id=task_id).first()
        if task is None:
            raise MissingResource(task_id)
        else:
            task_dict = task_serializer(task)
            if 'worker_name' in task_dict:
                queue_name = Worker(task_dict['worker_name'], datetime.now()).queue_name
                task_dict.update({'queue': queue_name})
            return self.ok(task_dict)

    @auth_required(DELETE)
    def DELETE(self, task_id):
        """
        Cancel the task that is represented by the given task_id, unless it is already in a
        complete state.

        :param task_id: The ID of the task you wish to cancel
        :type  task_id: basestring
        """
        tasks.cancel(task_id)
        return self.ok(None)


# mapped to /v2/tasks/
TASK_URLS = (
    '/', TaskCollection,
    '/search/', SearchTaskCollection,
    '/([^/]+)/', TaskResource,
)
task_application = web.application(TASK_URLS, globals())
