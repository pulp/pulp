import unittest

import mock

from pulp.server import exceptions
from pulp.server.controllers import distributor
from pulp.server.db import model


@mock.patch('pulp.server.controllers.distributor.RepoConfigConduit')
@mock.patch('pulp.server.controllers.distributor.PluginCallConfiguration')
@mock.patch('pulp.server.controllers.distributor.plugin_api')
@mock.patch('pulp.server.controllers.distributor.model')
class TestAddDistributor(unittest.TestCase):
    """
    Tests for adding a distributor.
    """

    def test_invalid_distributor_type(self, m_model, m_plug_api, m_plug_call_conf,
                                      m_repo_conf_conduit):
        """
        Ensure that invalid distributor types stop the creation of a distributor.
        """
        m_plug_api.is_valid_distributor.return_value = False
        self.assertRaises(exceptions.InvalidValue, distributor.add_distributor, 'repoid',
                          'dist_type', None, False)

    def test_invalid_distributor(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit):
        """
        Raise when the plugin detects an invalid distributor.
        """
        m_repo_obj = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_model.Distributor.objects.get_or_404.side_effect = exceptions.MissingResource
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_dist_inst.validate_config.return_value = False

        self.assertRaises(exceptions.PulpDataException, distributor.add_distributor, 'repoid',
                          'dist_type', None, False)

        m_plug_call_conf.assert_called_once_with(m_plug_config, None)
        m_repo_conf_conduit.assert_called_once_with('dist_type')
        m_dist_inst.validate_config.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value,
            m_repo_conf_conduit.return_value)

    def test_invalid_dist_msg(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit):
        """
        Raise with a message when the plugin detects an invalid distributor includes a message.
        """
        m_repo_obj = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_model.Distributor.objects.get_or_404.side_effect = exceptions.MissingResource
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_dist_inst.validate_config.return_value = (False, 'test_message')

        self.assertRaises(exceptions.PulpDataException, distributor.add_distributor, 'repoid',
                          'dist_type', None, False)

        m_plug_call_conf.assert_called_once_with(m_plug_config, None)
        m_repo_conf_conduit.assert_called_once_with('dist_type')
        m_dist_inst.validate_config.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value,
            m_repo_conf_conduit.return_value)

    @mock.patch('pulp.server.controllers.distributor.uuid')
    def test_minimal_distributor(self, m_uuid, m_model, m_plug_api, m_plug_call_conf,
                                 m_repo_conf_conduit):
        """
        Create the simplest possible distributor.
        """
        m_repo_obj = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_model.Distributor.objects.get_or_404.side_effect = exceptions.MissingResource
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_dist_inst.validate_config.return_value = True
        new_dist = m_model.Distributor.return_value
        mock_id = str(m_uuid.uuid4.return_value)

        result = distributor.add_distributor('repoid', 'dist_type', None, False)

        m_plug_call_conf.assert_called_once_with(m_plug_config, None)
        m_repo_conf_conduit.assert_called_once_with('dist_type')
        m_dist_inst.validate_config.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value,
            m_repo_conf_conduit.return_value)
        m_dist_inst.distributor_added.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value)
        m_model.Distributor.assert_called_once_with('repoid', mock_id, 'dist_type', None, False)
        new_dist.save.assert_called_once_with()
        self.assertTrue(result is new_dist)

    def test_distributor_with_id(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit):
        """
        Create a distributor with a specified distributor id.
        """
        m_repo_obj = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_model.Distributor.objects.get_or_404.side_effect = exceptions.MissingResource
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_dist_inst.validate_config.return_value = True
        new_dist = m_model.Distributor.return_value

        result = distributor.add_distributor('repoid', 'dist_type', None, False,
                                             distributor_id='fake_id')

        m_plug_call_conf.assert_called_once_with(m_plug_config, None)
        m_repo_conf_conduit.assert_called_once_with('dist_type')
        m_dist_inst.validate_config.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value,
            m_repo_conf_conduit.return_value)
        m_dist_inst.distributor_added.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value)
        m_model.Distributor.assert_called_once_with('repoid', 'fake_id', 'dist_type', None, False)
        new_dist.save.assert_called_once_with()
        self.assertTrue(result is new_dist)

    @mock.patch('pulp.server.controllers.distributor.delete')
    def test_dup_distributor(self, m_delete, m_model, m_plug_api, m_plug_call_conf,
                             m_repo_conf_conduit):
        """
        Ensure that an already existing distributor is removed and recreated.
        """
        m_repo_obj = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_dist_inst.validate_config.return_value = True
        new_dist = m_model.Distributor.return_value

        result = distributor.add_distributor('repoid', 'dist_type', None, False,
                                             distributor_id='dist_id')

        m_delete.assert_called_once_with('repoid', 'dist_id')
        m_plug_call_conf.assert_called_once_with(m_plug_config, None)
        m_repo_conf_conduit.assert_called_once_with('dist_type')
        m_dist_inst.validate_config.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value,
            m_repo_conf_conduit.return_value)
        m_dist_inst.distributor_added.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value)
        m_model.Distributor.assert_called_once_with('repoid', 'dist_id', 'dist_type', None, False)
        new_dist.save.assert_called_once_with()
        self.assertTrue(result is new_dist)

    def test_distributor_w_conf(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit):
        """
        Test that the repo_plugin_config is cleaned and passed.
        """
        m_repo_obj = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_model.Distributor.objects.get_or_404.side_effect = exceptions.MissingResource
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_dist_inst.validate_config.return_value = True
        new_dist = m_model.Distributor.return_value

        result = distributor.add_distributor('repoid', 'dist_type', {'mock': 'conf', 'none': None},
                                             False, distributor_id='fake_id')

        m_plug_call_conf.assert_called_once_with(m_plug_config, {'mock': 'conf'})
        m_repo_conf_conduit.assert_called_once_with('dist_type')
        m_dist_inst.validate_config.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value,
            m_repo_conf_conduit.return_value)
        m_dist_inst.distributor_added.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value)
        m_model.Distributor.assert_called_once_with('repoid', 'fake_id', 'dist_type',
                                                    {'mock': 'conf'}, False)
        new_dist.save.assert_called_once_with()
        self.assertTrue(result is new_dist)


@mock.patch('pulp.server.controllers.distributor.TaskResult')
@mock.patch('pulp.server.controllers.distributor.PluginCallConfiguration')
@mock.patch('pulp.server.controllers.distributor.plugin_api')
@mock.patch('pulp.server.controllers.distributor.managers')
@mock.patch('pulp.server.controllers.distributor.model.Distributor.objects')
@mock.patch('pulp.server.controllers.distributor.model.Repository.objects')
class TestDelete(unittest.TestCase):
    """
    Tests for the deletion of a distributor.
    """

    def test_expected(self, m_repo_qs, m_dist_qs, m_managers, m_plug_api, m_plug_call_conf, m_task):
        """
        Test removal of a distributor with minimal valid arguments.
        """
        m_repo_obj = m_repo_qs.get_repo_or_missing_resource.return_value
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_repo_pub_sched_man = m_managers.repo_publish_schedule_manager.return_value
        m_bind_man = m_managers.consumer_bind_manager.return_value
        m_bind_man.find_by_distributor.return_value = []

        result = distributor.delete('rid', 'did')

        m_repo_pub_sched_man.delete_by_distributor_id.assert_called_once_with('rid', 'did')
        m_dist_inst.distributor_removed.assert_called_once_with(
            m_repo_obj.to_transfer_repo.return_value, m_plug_call_conf.return_value)
        m_dist_qs.get_or_404.return_value.delete.assert_called_once_with()
        m_task.assert_called_once_with(error=None, spawned_tasks=[])
        self.assertTrue(result is m_task.return_value)

    def test_bindings(self, m_repo_qs, m_dist_qs, m_managers, m_plug_api, m_plug_call_conf, m_task):
        """
        Test that consumers are unbound after a distributor is removed.
        """
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_bind_man = m_managers.consumer_bind_manager.return_value
        m_bind = {'consumer_id': 'cid', 'repo_id': 'rid', 'distributor_id': 'did'}
        m_bind_man.find_by_distributor.return_value = [m_bind]
        m_bind_man.unbind.return_value = None

        result = distributor.delete('rid', 'did')

        m_bind_man.unbind.assert_called_once_with(m_bind['consumer_id'], m_bind['repo_id'],
                                                  m_bind['distributor_id'], {})
        m_task.assert_called_once_with(error=None, spawned_tasks=[])
        self.assertTrue(result is m_task.return_value)

    def test_unbind_w_spawned_tasks(self, m_repo_qs, m_dist_qs, m_managers, m_plug_api,
                                    m_plug_call_conf, m_task):
        """
        Ensure that when unbind spawns tasks, they are included in the result.
        """
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_bind_man = m_managers.consumer_bind_manager.return_value
        m_bind = {'consumer_id': 'cid', 'repo_id': 'rid', 'distributor_id': 'did'}
        m_bind_man.find_by_distributor.return_value = [m_bind]
        m_bind_man.unbind.return_value = mock.MagicMock(spawned_tasks=['another_task'])

        result = distributor.delete('rid', 'did')

        m_bind_man.unbind.assert_called_once_with(m_bind['consumer_id'], m_bind['repo_id'],
                                                  m_bind['distributor_id'], {})
        m_task.assert_called_once_with(error=None, spawned_tasks=['another_task'])
        self.assertTrue(result is m_task.return_value)

    @mock.patch('pulp.server.controllers.distributor.exceptions.PulpCodedException')
    def test_unbind_w_error(self, m_exception, m_repo_qs, m_dist_qs, m_managers, m_plug_api,
                            m_plug_call_conf, m_task):
        """
        Test handling of errors raised by unbind.
        """
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_bind_man = m_managers.consumer_bind_manager.return_value
        m_bind = {'consumer_id': 'cid', 'repo_id': 'rid', 'distributor_id': 'did'}
        m_bind_man.find_by_distributor.return_value = [m_bind]
        m_bind_man.unbind.side_effect = Exception('test e')

        result = distributor.delete('rid', 'did')

        m_bind_man.unbind.assert_called_once_with(m_bind['consumer_id'], m_bind['repo_id'],
                                                  m_bind['distributor_id'], {})
        m_task.assert_called_once_with(error=m_exception.return_value, spawned_tasks=[])
        self.assertTrue(result is m_task.return_value)


@mock.patch('pulp.server.controllers.distributor.update')
@mock.patch('pulp.server.controllers.distributor.delete')
@mock.patch('pulp.server.controllers.distributor.tags')
class TestQueueTasks(unittest.TestCase):
    """
    Tests for queueing distributor tasks.
    """

    def test_queue_delete(self, m_tags, m_delete, m_update):
        """
        Ensure that queueing a delete task uses the proper tags.
        """
        m_task_tags = [m_tags.resource_tag(), m_tags.resource_tag(), m_tags.action_tag()]
        dist = model.Distributor('rid', 'did', 'd_type_id', {}, False)

        result = distributor.queue_delete(dist)
        m_delete.apply_async_with_reservation.assert_called_once_with(
            m_tags.RESOURCE_REPOSITORY_TYPE, dist.repo_id, ['rid', 'did'], tags=m_task_tags)
        self.assertTrue(result is m_delete.apply_async_with_reservation.return_value)

    def test_queue_update(self, m_tags, m_delete, m_update):
        """
        Ensure that queueing an update task uses the proper tags.
        """
        m_task_tags = [m_tags.resource_tag(), m_tags.resource_tag(), m_tags.action_tag()]
        dist = model.Distributor('rid', 'did', 'd_type_id', {}, False)

        result = distributor.queue_update(dist, {'m': 'conf'}, {'m': 'delta'})
        m_update.apply_async_with_reservation.assert_called_once_with(
            m_tags.RESOURCE_REPOSITORY_TYPE, dist.repo_id,
            ['rid', 'did', {'m': 'conf'}, {'m': 'delta'}], tags=m_task_tags)
        self.assertTrue(result is m_update.apply_async_with_reservation.return_value)


@mock.patch('pulp.server.controllers.distributor.TaskResult')
@mock.patch('pulp.server.controllers.distributor.managers')
@mock.patch('pulp.server.controllers.distributor.RepoConfigConduit')
@mock.patch('pulp.server.controllers.distributor.PluginCallConfiguration')
@mock.patch('pulp.server.controllers.distributor.plugin_api')
@mock.patch('pulp.server.controllers.distributor.model')
class TestUpdate(unittest.TestCase):
    """
    Tests for updating a distributor.
    """

    def test_auto_pub_not_bool(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit,
                               m_managers, m_task):
        """
        Test that when auto_publish is not a bool that an InvalidValue is raised.
        """
        self.assertRaises(exceptions.InvalidValue, distributor.update, 'rid', 'did', {},
                          {'auto_publish': 'not bool'})

    def test_invalid_config(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit,
                            m_managers, m_task):
        """
        Ensure that when the plugin detects an invalid distributor, raise.
        """
        repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        dist = m_model.Distributor.objects.get_or_404.return_value
        dist.config = {'dist': 'conf'}
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_call_conf = m_plug_call_conf.return_value
        m_conf_conduit = m_repo_conf_conduit.return_value
        m_dist_inst.validate_config.return_value = False

        self.assertRaises(
            exceptions.PulpDataException, distributor.update, dist, {'dist': 'conf'}, {})

        m_plug_api.get_distributor_by_id.assert_called_once_with(dist.distributor_type_id)
        m_plug_call_conf.assert_called_once_with(m_plug_config, {'dist': 'conf'})
        m_repo_conf_conduit.assert_called_once_with(dist.distributor_type_id)
        m_dist_inst.validate_config.assert_called_once_with(repo.to_transfer_repo.return_value,
                                                            m_call_conf, m_conf_conduit)

    def test_invalid_config_msg(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit,
                                m_managers, m_task):
        """
        Ensure that when the plugin detects an invalid distributor and includes a message, raise.
        """
        repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        dist = m_model.Distributor.objects.get_or_404.return_value
        dist.config = {'dist': 'conf'}
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_call_conf = m_plug_call_conf.return_value
        m_conf_conduit = m_repo_conf_conduit.return_value
        m_dist_inst.validate_config.return_value = (False, 'test_message')

        self.assertRaises(
            exceptions.PulpDataException, distributor.update, dist, {'dist': 'conf'}, {})

        m_plug_api.get_distributor_by_id.assert_called_once_with(dist.distributor_type_id)
        m_plug_call_conf.assert_called_once_with(m_plug_config, {'dist': 'conf'})
        m_repo_conf_conduit.assert_called_once_with(dist.distributor_type_id)
        m_dist_inst.validate_config.assert_called_once_with(repo.to_transfer_repo.return_value,
                                                            m_call_conf, m_conf_conduit)

    def test_minimal(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit, m_managers,
                     m_task):
        """
        Test that a minimal update works as expected.
        """
        repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        dist = m_model.Distributor.objects.get_or_404.return_value
        dist.config = {}
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_call_conf = m_plug_call_conf.return_value
        m_conf_conduit = m_repo_conf_conduit.return_value
        m_dist_inst.validate_config.return_value = True
        m_bind_man = m_managers.consumer_bind_manager.return_value
        m_bind_man.find_by_distributor.return_value = []

        result = distributor.update('rid', 'did', {'dist': 'conf'}, {})

        m_plug_api.get_distributor_by_id.assert_called_once_with(dist.distributor_type_id)
        m_plug_call_conf.assert_called_once_with(m_plug_config, {'dist': 'conf'})
        m_repo_conf_conduit.assert_called_once_with(dist.distributor_type_id)
        m_dist_inst.validate_config.assert_called_once_with(repo.to_transfer_repo.return_value,
                                                            m_call_conf, m_conf_conduit)
        m_model.Distributor.SERIALIZER.assert_called_once_with(dist)
        m_task.assert_called_once_with(m_model.Distributor.SERIALIZER.return_value.data,
                                       error=None, spawned_tasks=[])
        self.assertTrue(result is m_task.return_value)

    def test_remove_none_values(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit,
                                m_managers, m_task):
        """
        Ensure that None value in the update removes the associated key from the distributor config.
        """
        repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        dist = m_model.Distributor.objects.get_or_404.return_value
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_call_conf = m_plug_call_conf.return_value
        m_conf_conduit = m_repo_conf_conduit.return_value
        m_dist_inst.validate_config.return_value = True
        m_bind_man = m_managers.consumer_bind_manager.return_value
        m_bind_man.find_by_distributor.return_value = []

        result = distributor.update('rid', 'did', {'rm': None}, {})

        m_plug_api.get_distributor_by_id.assert_called_once_with(dist.distributor_type_id)
        m_plug_call_conf.assert_called_once_with(m_plug_config, dist.config)
        m_repo_conf_conduit.assert_called_once_with(dist.distributor_type_id)
        m_dist_inst.validate_config.assert_called_once_with(repo.to_transfer_repo.return_value,
                                                            m_call_conf, m_conf_conduit)
        m_model.Distributor.SERIALIZER.assert_called_once_with(dist)
        m_task.assert_called_once_with(m_model.Distributor.SERIALIZER.return_value.data,
                                       error=None, spawned_tasks=[])
        self.assertTrue(result is m_task.return_value)

    def test_bindings(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit, m_managers,
                      m_task):
        """
        Ensure that consumers are properly rebound after the distributor is updated.
        """
        repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        dist = m_model.Distributor.objects.get_or_404.return_value
        dist.config = {'dist': 'conf'}
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_call_conf = m_plug_call_conf.return_value
        m_conf_conduit = m_repo_conf_conduit.return_value
        m_dist_inst.validate_config.return_value = True
        m_bind_man = m_managers.consumer_bind_manager.return_value
        m_bind = {'consumer_id': 'cid', 'repo_id': 'rid', 'distributor_id': 'did',
                  'notify_agent': 'ag', 'binding_config': 'bind_conf'}
        m_bind_man.find_by_distributor.return_value = [m_bind]
        m_bind_man.bind.return_value = None

        result = distributor.update(dist, {'dist': 'conf'}, {})

        m_plug_api.get_distributor_by_id.assert_called_once_with(dist.distributor_type_id)
        m_plug_call_conf.assert_called_once_with(m_plug_config, {'dist': 'conf'})
        m_repo_conf_conduit.assert_called_once_with(dist.distributor_type_id)
        m_dist_inst.validate_config.assert_called_once_with(repo.to_transfer_repo.return_value,
                                                            m_call_conf, m_conf_conduit)
        m_model.Distributor.SERIALIZER.assert_called_once_with(dist)
        m_task.assert_called_once_with(m_model.Distributor.SERIALIZER.return_value.data,
                                       error=None, spawned_tasks=[])
        m_bind_man.bind.assert_called_once_with(
            m_bind['consumer_id'], m_bind['repo_id'], m_bind['distributor_id'],
            m_bind['notify_agent'], m_bind['binding_config'], {})
        self.assertTrue(result is m_task.return_value)

    def test_bindings_spawn(self, m_model, m_plug_api, m_plug_call_conf, m_repo_conf_conduit,
                            m_managers, m_task):
        """
        Ensure that when tasks are spawned by binding consumers, they are included in the result.
        """
        repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        dist = m_model.Distributor.objects.get_or_404.return_value
        dist.config = {'dist': 'conf'}
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_call_conf = m_plug_call_conf.return_value
        m_conf_conduit = m_repo_conf_conduit.return_value
        m_dist_inst.validate_config.return_value = True
        m_bind_man = m_managers.consumer_bind_manager.return_value
        m_bind = {'consumer_id': 'cid', 'repo_id': 'rid', 'distributor_id': 'did',
                  'notify_agent': 'ag', 'binding_config': 'bind_conf'}
        m_bind_man.find_by_distributor.return_value = [m_bind]
        m_bind_man.bind.return_value = mock.MagicMock(spawned_tasks=['spawned task'])

        result = distributor.update(dist, {'dist': 'conf'}, {})

        m_plug_api.get_distributor_by_id.assert_called_once_with(dist.distributor_type_id)
        m_plug_call_conf.assert_called_once_with(m_plug_config, {'dist': 'conf'})
        m_repo_conf_conduit.assert_called_once_with(dist.distributor_type_id)
        m_dist_inst.validate_config.assert_called_once_with(repo.to_transfer_repo.return_value,
                                                            m_call_conf, m_conf_conduit)
        m_model.Distributor.SERIALIZER.assert_called_once_with(dist)
        m_task.assert_called_once_with(m_model.Distributor.SERIALIZER.return_value.data,
                                       error=None, spawned_tasks=['spawned task'])
        m_bind_man.bind.assert_called_once_with(
            m_bind['consumer_id'], m_bind['repo_id'], m_bind['distributor_id'],
            m_bind['notify_agent'], m_bind['binding_config'], {})
        self.assertTrue(result is m_task.return_value)

    @mock.patch('pulp.server.controllers.distributor.exceptions.PulpCodedException')
    def test_bindings_err(self, m_exception, m_model, m_plug_api, m_plug_call_conf,
                          m_repo_conf_conduit, m_managers, m_task):
        """
        Test handling of errors raised by binding consumers.
        """
        repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        dist = m_model.Distributor.objects.get_or_404.return_value
        dist.config = {'dist': 'conf'}
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_call_conf = m_plug_call_conf.return_value
        m_conf_conduit = m_repo_conf_conduit.return_value
        m_dist_inst.validate_config.return_value = True
        m_bind_man = m_managers.consumer_bind_manager.return_value
        m_bind = {'consumer_id': 'cid', 'repo_id': 'rid', 'distributor_id': 'did',
                  'notify_agent': 'ag', 'binding_config': 'bind_conf'}
        m_bind_man.find_by_distributor.return_value = [m_bind]
        m_bind_man.bind.side_effect = Exception("dang")

        result = distributor.update(dist, {'dist': 'conf'}, {})

        m_plug_api.get_distributor_by_id.assert_called_once_with(dist.distributor_type_id)
        m_plug_call_conf.assert_called_once_with(m_plug_config, {'dist': 'conf'})
        m_repo_conf_conduit.assert_called_once_with(dist.distributor_type_id)
        m_dist_inst.validate_config.assert_called_once_with(repo.to_transfer_repo.return_value,
                                                            m_call_conf, m_conf_conduit)
        m_model.Distributor.SERIALIZER.assert_called_once_with(dist)
        m_task.assert_called_once_with(m_model.Distributor.SERIALIZER.return_value.data,
                                       error=m_exception.return_value, spawned_tasks=[])
        m_bind_man.bind.assert_called_once_with(
            m_bind['consumer_id'], m_bind['repo_id'], m_bind['distributor_id'],
            m_bind['notify_agent'], m_bind['binding_config'], {})
        self.assertTrue(result is m_task.return_value)


@mock.patch('pulp.server.controllers.distributor.PluginCallConfiguration')
@mock.patch('pulp.server.controllers.distributor.plugin_api')
@mock.patch('pulp.server.controllers.distributor.model')
class TestCreateBindPayload(unittest.TestCase):
    """
    Tests for creating a consumer bind payload.
    """

    def test_expected(self, m_model, m_plug_api, m_plug_call_conf):
        """
        Ensure that the appropriate call is made to the plugin to build a payload.
        """
        repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        dist = m_model.Distributor.objects.get_or_404.return_value
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)

        result = distributor.create_bind_payload('rid', 'did', {'bind': 'conf'})

        m_plug_api.get_distributor_by_id.assert_called_once_with(dist.distributor_type_id)
        m_plug_call_conf.assert_called_once_with(m_plug_config, dist.config)
        m_dist_inst.create_consumer_payload.assert_called_once_with(
            repo.to_transfer_repo(), m_plug_call_conf.return_value, {'bind': 'conf'})
        self.assertTrue(result is m_dist_inst.create_consumer_payload.return_value)

    def test_exception(self, m_model, m_plug_api, m_plug_call_conf):
        """
        Test handling of an exception from the plugin when attempting to build a payload.
        """
        repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        dist = m_model.Distributor.objects.get_or_404.return_value
        m_dist_inst = mock.MagicMock()
        m_plug_config = mock.MagicMock()
        m_plug_api.get_distributor_by_id.return_value = (m_dist_inst, m_plug_config)
        m_dist_inst.create_consumer_payload.side_effect = Exception("so close")

        self.assertRaises(exceptions.PulpExecutionException, distributor.create_bind_payload,
                          'rid', 'did', {'bind': 'conf'})

        m_plug_api.get_distributor_by_id.assert_called_once_with(dist.distributor_type_id)
        m_plug_call_conf.assert_called_once_with(m_plug_config, dist.config)
        m_dist_inst.create_consumer_payload.assert_called_once_with(
            repo.to_transfer_repo(), m_plug_call_conf.return_value, {'bind': 'conf'})
