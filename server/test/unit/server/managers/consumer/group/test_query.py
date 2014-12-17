"""
This module contains tests for the pulp.server.managers.consumer.group.query module.
"""
import mock

from .....import base
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers.consumer.group import query


class ConsumerGroupQueryManagerTests(base.PulpServerTests):
    def setUp(self):
        base.PulpServerTests.setUp(self)

        self.query_manager = query.ConsumerGroupQueryManager()

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_find_by_criteria(self, mock_query):
        criteria = Criteria()
        self.query_manager.find_by_criteria(criteria)
        mock_query.assert_called_once_with(criteria)
