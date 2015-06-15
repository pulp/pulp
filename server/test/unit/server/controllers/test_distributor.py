from mock import patch, ANY

from pulp.devel.unit import util
from pulp.devel.unit.base import PulpCeleryTaskTests
from pulp.server.async.tasks import TaskResult
from pulp.server.exceptions import PulpException, error_codes
from pulp.server.managers import factory
from pulp.server.controllers import distributor as dist_controller


factory.initialize()


class TestDistributorDelete(PulpCeleryTaskTests):

    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_distributor_manager')
    def test_distributor_delete_no_bindings(self, mock_dist_manager, mock_bind_manager):
        result = dist_controller.delete('foo-id', 'bar-id')
        mock_dist_manager.return_value.remove_distributor.assert_called_with('foo-id', 'bar-id')
        self.assertTrue(isinstance(result, TaskResult))

    @patch('pulp.server.controllers.consumer.unbind')
    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_distributor_manager')
    def test_distributor_delete_with_bindings(self, mock_dist_manager, mock_bind_manager,
                                              mock_unbind):
        mock_bind_manager.return_value.find_by_distributor.return_value = [
            {'consumer_id': 'foo', 'repo_id': 'repo-foo', 'distributor_id': 'dist-id'}]
        mock_unbind.return_value = TaskResult(spawned_tasks=[{'task_id': 'foo-request-id'}])
        result = dist_controller.delete('foo-id', 'bar-id')
        mock_dist_manager.return_value.remove_distributor.assert_called_with('foo-id', 'bar-id')
        mock_unbind.assert_called_once_with('foo', 'repo-foo', 'dist-id', ANY)
        self.assertEquals(result.spawned_tasks[0], {'task_id': 'foo-request-id'})

    @patch('pulp.server.controllers.consumer.unbind')
    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_distributor_manager')
    def test_distributor_delete_with_agent_errors(self, mock_dist_manager, mock_bind_manager,
                                                  mock_unbind):
        mock_bind_manager.return_value.find_by_repo.return_value = [
            {'consumer_id': 'foo', 'repo_id': 'repo-foo', 'distributor_id': 'dist-id'}]

        mock_bind_manager.return_value.find_by_distributor.return_value = [
            {'consumer_id': 'foo', 'repo_id': 'repo-foo', 'distributor_id': 'dist-id'}]
        side_effect_exception = PulpException('foo')
        mock_unbind.side_effect = side_effect_exception

        result = dist_controller.delete('foo-id', 'bar-id')

        mock_unbind.assert_called_once_with('foo', 'repo-foo', 'dist-id', ANY)
        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0003)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)


class TestDistributorUpdate(PulpCeleryTaskTests):

    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_distributor_manager')
    def test_distributor_update_no_bindings(self, mock_dist_manager, mock_bind_manager):
        config = {'configvalue': 'baz'}
        generated_distributor = {'foo': 'bar'}
        mock_dist_manager.return_value.update_distributor_config.return_value = \
            generated_distributor

        # Use None for the delta value to ensure it doesn't throw an exception
        result = dist_controller.update('foo-id', 'bar-id', config, None)

        mock_dist_manager.return_value.update_distributor_config. \
            assert_called_with('foo-id', 'bar-id', config, None)
        self.assertTrue(isinstance(result, TaskResult))
        util.compare_dict(generated_distributor, result.return_value)
        self.assertEquals(None, result.error)

    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_distributor_manager')
    def test_distributor_update_with_auto_publish(self, mock_dist_manager, mock_bind_manager):
        config = {}
        delta = {'auto_publish': True}
        result = dist_controller.update('foo-id', 'bar-id', {}, delta)
        mock_dist_manager.return_value.update_distributor_config. \
            assert_called_with('foo-id', 'bar-id', config, True)
        self.assertTrue(isinstance(result, TaskResult))

    @patch('pulp.server.controllers.consumer.bind')
    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_distributor_manager')
    def test_distributor_update_with_bindings(self, mock_dist_manager, mock_bind_manager,
                                              mock_bind):
        generated_distributor = {'foo': 'bar'}
        mock_dist_manager.return_value.update_distributor_config.return_value = \
            generated_distributor
        mock_bind_manager.return_value.find_by_distributor.return_value = [
            {'consumer_id': 'foo', 'repo_id': 'repo-foo', 'distributor_id': 'dist-id',
             'notify_agent': True, 'binding_config': {'conf': 'baz'}}]

        mock_bind.return_value = TaskResult(spawned_tasks=[{'task_id': 'foo-request-id'}])

        result = dist_controller.update('foo-id', 'bar-id', {}, None)
        self.assertEquals(None, result.error)
        mock_bind.assert_called_once_with('foo', 'repo-foo', 'dist-id', True, {'conf': 'baz'}, ANY)
        self.assertEquals(result.spawned_tasks[0], {'task_id': 'foo-request-id'})

    @patch('pulp.server.controllers.consumer.bind')
    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_distributor_manager')
    def test_distributor_update_with_agent_errors(self, mock_dist_manager, mock_bind_manager,
                                                  mock_bind):
        generated_distributor = {'foo': 'bar'}
        mock_dist_manager.return_value.update_distributor_config.return_value = \
            generated_distributor
        mock_bind_manager.return_value.find_by_distributor.return_value = [
            {'consumer_id': 'foo', 'repo_id': 'repo-foo', 'distributor_id': 'dist-id',
             'notify_agent': True, 'binding_config': {'conf': 'baz'}}]
        side_effect_exception = PulpException('foo')
        mock_bind.side_effect = side_effect_exception

        result = dist_controller.update('foo-id', 'bar-id', {}, None)

        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0002)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)
