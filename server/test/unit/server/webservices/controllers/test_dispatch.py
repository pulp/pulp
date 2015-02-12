"""
This module contains tests for the pulp.server.webservices.dispatch module.
"""
import json

import mock

from pulp.devel.unit.server.base import PulpWebservicesTests
from pulp.devel.unit.util import compare_dict
from pulp.server.auth import authorization
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.webservices.controllers import dispatch as dispatch_controller


class SearchTaskCollectionTests(PulpWebservicesTests):

    def get_task(self):
        return TaskStatus(task_id='foo', spawned_tasks=['bar', 'baz'])

    @mock.patch('pulp.server.webservices.controllers.dispatch.SearchTaskCollection.'
                '_get_query_results_from_get', autospec=True)
    def test_get(self, mock_get_results):
        search_controller = dispatch_controller.SearchTaskCollection()
        mock_get_results.return_value = [self.get_task()]
        processed_tasks_json = search_controller.GET()

        # Mimic the processing
        updated_task = dispatch_controller.task_serializer(self.get_task())
        processed_tasks = json.loads(processed_tasks_json)
        compare_dict(updated_task, processed_tasks[0])

        # validate the permissions
        self.validate_auth(authorization.READ)

    @mock.patch('pulp.server.webservices.controllers.dispatch.SearchTaskCollection.'
                '_get_query_results_from_post', autospec=True)
    def test_post(self, mock_get_results):
        search_controller = dispatch_controller.SearchTaskCollection()
        mock_get_results.return_value = [self.get_task()]
        processed_tasks_json = search_controller.POST()

        # Mimic the processing
        updated_task = dispatch_controller.task_serializer(self.get_task())
        processed_tasks = json.loads(processed_tasks_json)
        compare_dict(updated_task, processed_tasks[0])

        # validate the permissions
        self.validate_auth(authorization.READ)
