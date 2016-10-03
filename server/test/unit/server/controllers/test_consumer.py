import unittest

from mock import patch

from pulp.server.async.tasks import TaskResult
from pulp.server.controllers import consumer


@patch('pulp.server.controllers.consumer.managers')
class TestBind(unittest.TestCase):

    def test_bind(self, mock_bind_manager):
        binding_config = {'binding': 'foo'}
        result = consumer.bind('foo_consumer_id', 'foo_repo_id', 'foo_distributor_id',
                               False, binding_config)

        mock_bind_manager.consumer_bind_manager.return_value.bind.assert_called_once_with(
            'foo_consumer_id', 'foo_repo_id', 'foo_distributor_id',
            False, binding_config)

        self.assertTrue(isinstance(result, TaskResult))
        self.assertEquals(mock_bind_manager.consumer_bind_manager.return_value.bind.return_value,
                          result.return_value)


@patch('pulp.server.controllers.consumer.managers')
class TestUnbind(unittest.TestCase):

    def test_unbind(self, mock_bind_manager):
        binding_config = {}
        mock_bind_manager.consumer_bind_manager.return_value.get_bind.return_value = binding_config
        result = consumer.unbind('foo_consumer_id', 'foo_repo_id', 'foo_distributor_id')

        mock_bind_manager.consumer_bind_manager.return_value.delete.assert_called_once_with(
            'foo_consumer_id', 'foo_repo_id', 'foo_distributor_id', True)

        self.assertEqual(result.error, None)
        self.assertEqual(result.spawned_tasks, [])


@patch('pulp.server.controllers.consumer.managers')
class TestForceUnbind(unittest.TestCase):

    def test_unbind(self, mock_bind_manager):
        binding_config = {}
        mock_bind_manager.consumer_bind_manager.return_value.get_bind.return_value = binding_config
        result = consumer.force_unbind('foo_consumer_id', 'foo_repo_id', 'foo_distributor_id')

        mock_bind_manager.consumer_bind_manager.return_value.delete.assert_called_once_with(
            'foo_consumer_id', 'foo_repo_id', 'foo_distributor_id', True)

        self.assertEqual(result.error, None)
        self.assertEqual(result.return_value, None)
        self.assertEqual(result.spawned_tasks, [])
