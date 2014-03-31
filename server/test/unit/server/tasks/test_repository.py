# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from mock import patch, ANY


from pulp.common.tags import action_tag, resource_tag, RESOURCE_REPOSITORY_TYPE
from pulp.devel.unit import util
from pulp.devel.unit.base import PulpCeleryTaskTests
from pulp.server.async.tasks import TaskResult
from pulp.server.exceptions import PulpException, error_codes
from pulp.server.tasks import repository


class TestDelete(PulpCeleryTaskTests):

    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_manager')
    def test_delete_no_bindings(self, mock_repo_manager, mock_bind_manager):
        result = repository.delete('foo-repo')
        mock_repo_manager.return_value.delete_repo.assert_called_with('foo-repo')
        self.assertTrue(isinstance(result, TaskResult))

    @patch('pulp.server.tasks.consumer.unbind')
    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_manager')
    def test_delete_with_bindings(self, mock_repo_manager, mock_bind_manager, mock_unbind):
        mock_bind_manager.return_value.find_by_repo.return_value = [
            {'consumer_id': 'foo', 'repo_id': 'repo-foo', 'distributor_id': 'dist-id'}]
        mock_unbind.return_value = TaskResult(spawned_tasks=[{'task_id': 'foo-request-id'}])
        result = repository.delete('foo-repo')
        mock_unbind.assert_called_once_with('foo', 'repo-foo', 'dist-id', ANY)
        self.assertEquals(result.spawned_tasks[0], {'task_id': 'foo-request-id'})

    @patch('pulp.server.tasks.consumer.unbind')
    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_manager')
    def test_delete_with_bindings_errors(self, mock_repo_manager, mock_bind_manager, mock_unbind):
        mock_bind_manager.return_value.find_by_repo.return_value = [
            {'consumer_id': 'foo', 'repo_id': 'repo-foo', 'distributor_id': 'dist-id'}]
        side_effect_exception = PulpException('foo')
        mock_unbind.side_effect = side_effect_exception
        result = repository.delete('foo-repo')
        mock_unbind.assert_called_once_with('foo', 'repo-foo', 'dist-id', ANY)
        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0007)
        error_dict = result.error.to_dict()
        self.assertTrue("Error occurred while cascading delete of repository"
                        in error_dict['description'])
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)


class TestDistributorDelete(PulpCeleryTaskTests):

    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_distributor_manager')
    def test_distributor_delete_no_bindings(self, mock_dist_manager, mock_bind_manager):
        result = repository.distributor_delete('foo-id', 'bar-id')
        mock_dist_manager.return_value.remove_distributor.assert_called_with('foo-id', 'bar-id')
        self.assertTrue(isinstance(result, TaskResult))

    @patch('pulp.server.tasks.consumer.unbind')
    @patch('pulp.server.managers.factory.consumer_bind_manager')
    @patch('pulp.server.managers.factory.repo_distributor_manager')
    def test_distributor_delete_with_bindings(self, mock_dist_manager, mock_bind_manager,
                                              mock_unbind):
        mock_bind_manager.return_value.find_by_distributor.return_value = [
            {'consumer_id': 'foo', 'repo_id': 'repo-foo', 'distributor_id': 'dist-id'}]
        mock_unbind.return_value = TaskResult(spawned_tasks=[{'task_id': 'foo-request-id'}])
        result = repository.distributor_delete('foo-id', 'bar-id')
        mock_dist_manager.return_value.remove_distributor.assert_called_with('foo-id', 'bar-id')
        mock_unbind.assert_called_once_with('foo', 'repo-foo', 'dist-id', ANY)
        self.assertEquals(result.spawned_tasks[0], {'task_id': 'foo-request-id'})

    @patch('pulp.server.tasks.consumer.unbind')
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

        result = repository.distributor_delete('foo-id', 'bar-id')

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

        #Use None for the delta value to ensure it doesn't throw an exception
        result = repository.distributor_update('foo-id', 'bar-id', config, None)

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
        result = repository.distributor_update('foo-id', 'bar-id', {}, delta)
        mock_dist_manager.return_value.update_distributor_config. \
            assert_called_with('foo-id', 'bar-id', config, True)
        self.assertTrue(isinstance(result, TaskResult))

    @patch('pulp.server.tasks.consumer.bind')
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

        result = repository.distributor_update('foo-id', 'bar-id', {}, None)
        self.assertEquals(None, result.error)
        mock_bind.assert_called_once_with('foo', 'repo-foo', 'dist-id', True, {'conf': 'baz'}, ANY)
        self.assertEquals(result.spawned_tasks[0], {'task_id': 'foo-request-id'})

    @patch('pulp.server.tasks.consumer.bind')
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

        result = repository.distributor_update('foo-id', 'bar-id', {}, None)

        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0002)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)


class TestRepositoryPublish(PulpCeleryTaskTests):

    @patch('pulp.server.tasks.repository.publish_task.apply_async_with_reservation')
    def test_publish(self, mock_publish_task):
        repo_id = 'foo'
        distributor_id = 'bar'
        overrides = 'baz'
        repository.publish(repo_id, distributor_id, overrides)
        kwargs = {
            'repo_id': repo_id,
            'distributor_id': distributor_id,
            'publish_config_override': overrides
        }
        tags = [resource_tag(RESOURCE_REPOSITORY_TYPE, repo_id), action_tag('publish')]
        mock_publish_task.assert_called_with(RESOURCE_REPOSITORY_TYPE, repo_id, tags=tags,
                                             kwargs=kwargs)


class TestRepositorySync(PulpCeleryTaskTests):

    @patch('pulp.server.tasks.repository.managers')
    def test_sync_alone(self, mock_managers):
        mock_managers.repo_sync_manager.return_value.sync.return_value = 'baz'
        result = repository.sync_with_auto_publish('foo', 'bar')
        self.assertTrue(isinstance(result, TaskResult))
        self.assertEquals(result.return_value, 'baz')

    @patch('pulp.server.tasks.repository.publish_task.apply_async_with_reservation')
    @patch('pulp.server.tasks.repository.managers')
    def test_sync_with_publish(self, mock_managers, mock_publish):
        mock_managers.repo_sync_manager.return_value.sync.return_value = 'baz'
        mock_managers.repo_publish_manager.return_value.auto_distributors.return_value = \
            [{'id': 'flux'}]
        mock_publish.return_value = 'fish'
        result = repository.sync_with_auto_publish('foo', 'bar')
        self.assertTrue(isinstance(result, TaskResult))
        self.assertEquals(result.spawned_tasks, ['fish', ])
