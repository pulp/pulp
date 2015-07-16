"""
This module contains bindings to the Task APIs.
"""

from pulp.bindings.base import PulpAPI
from pulp.bindings.responses import Task
from pulp.bindings.search import SearchAPI
import pulp.common.tags as tag_util


class TasksAPI(PulpAPI):

    def __init__(self, pulp_connection):
        super(TasksAPI, self).__init__(pulp_connection)

    def cancel_task(self, task_id):
        """
        Cancels the given task. The task must either be an operation on the
        server that supports cancelling or it must not have begun to execute
        yet.

        @param task_id: ID retrieved
        @return:
        """
        path = '/v2/tasks/%s/' % task_id
        response = self.server.DELETE(path)
        return response

    def get_task(self, task_id):
        """
        Retrieves the status of the given task if it exists.

        @return: response with a Task object in the response_body
        @rtype:  Response

        @raise NotFoundException: if there is no task with the given ID
        """
        path = '/v2/tasks/%s/' % task_id
        response = self.server.GET(path)

        # Since it was a 200, the connection parsed the response body into a
        # Document. We know this will be task data, so convert the object here.
        response.response_body = Task(response.response_body)
        return response

    def get_all_tasks(self, tags=()):
        """
        Retrieves all tasks in the system. If tags are specified, only tasks
        that contain all of the given tags are returned. All tasks will be
        represented by Task objects in a list in the response's response_body
        attribute. By default, completed tasks are excluded but they can be included by setting
        include_completed to True.

        :param tags:              if specified, only tasks that contain all tags in the given
                                  list are returned; None to return all tasks
        :type  tags:              list
        :return:                  response with a list of Task objects; empty list for no matching
                                  tasks
        :rtype:                   Response
        """
        path = '/v2/tasks/'
        tags = [('tag', t) for t in tags]

        response = self.server.GET(path, queries=tags)

        tasks = []
        # sort based on id, which is chronological in mongo
        for doc in sorted(response.response_body, key=lambda x: x['id']):
            tasks.append(Task(doc))

        response.response_body = tasks
        return response

    def purge_tasks(self, states=()):
        """
        Deletes completed tasks (except tasks in state 'canceled') in the system.
        If states are specified, only tasks that are in given states are purged.
        By default, all the completed tasks except tasks in state 'canceled', are purged.

        :param states:            tuple of states given by user through command line
                                  Default to return all completed tasks except 'canceled'
        :type  states:            tuple
        :return:                  HttpResponse from REST API;
        :rtype:                   Response
        """
        path = '/v2/tasks/'
        state = [('state', s) for s in states]
        response = self.server.DELETE(path, queries=state)

        return response

    def get_repo_tasks(self, repo_id):
        """
        Retrieves all tasks for the given repository.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @return: response with a list of Task objects; empty list for no matching tasks
        @rtype:  Response
        """
        repo_tag = tag_util.resource_tag(tag_util.RESOURCE_REPOSITORY_TYPE, repo_id)
        return self.get_all_tasks(tags=[repo_tag])

    def get_repo_sync_tasks(self, repo_id):
        """
        Retrieves all incomplete sync tasks for the given repository.

        :param repo_id: identifies the repo
        :type  repo_id: str
        :return:        response with a list of Task objects; empty list for no matching tasks
        :rtype:         Response
        """
        repo_tag = tag_util.resource_tag(tag_util.RESOURCE_REPOSITORY_TYPE, repo_id)
        sync_tag = tag_util.action_tag(tag_util.ACTION_SYNC_TYPE)
        return self.get_all_tasks(tags=[repo_tag, sync_tag])

    def get_repo_publish_tasks(self, repo_id):
        """
        Retrieves all publish tasks for the given repository.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @return: response with a list of Task objects; empty list for no matching tasks
        @rtype:  Response
        """
        repo_tag = tag_util.resource_tag(tag_util.RESOURCE_REPOSITORY_TYPE, repo_id)
        publish_tag = tag_util.action_tag(tag_util.ACTION_PUBLISH_TYPE)
        return self.get_all_tasks(tags=[repo_tag, publish_tag])


class TaskSearchAPI(SearchAPI):
    """
    Search Tasks.
    """
    PATH = 'v2/tasks/search/'

    def search(self, **kwargs):
        """
        Call the superclass search, and intercept the results so that we can turn the items back
        into Tasks.

        :param kwargs: Arguments to pass to SearchAPI.search()
        :type  kwargs: dict
        """
        tasks = super(TaskSearchAPI, self).search(**kwargs)

        return [Task(task) for task in sorted(tasks, key=lambda x: x['id'])]
