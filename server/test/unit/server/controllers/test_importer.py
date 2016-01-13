import mock
from mongoengine import ValidationError

from pulp.common.compat import unittest
from pulp.server import exceptions
from pulp.server.controllers import importer
from pulp.server.db import model


class MockException(Exception):
    """Used for tracking the handling of exceptions."""
    pass


class TestBuildResourceTag(unittest.TestCase):
    """
    Tests for building a resource tag.
    """

    def test_resource_tag(self):
        """
        Build an example resource tag.
        """
        tag = importer.build_resource_tag('repo_id', 'importer_id')
        self.assertEqual(tag, 'pulp:importer:repo_id:importer_id')


@mock.patch('pulp.server.controllers.importer._logger')
@mock.patch('pulp.server.controllers.importer.PluginCallConfiguration')
@mock.patch('pulp.server.controllers.importer.remove_importer')
@mock.patch('pulp.server.controllers.importer.clean_config_dict')
@mock.patch('pulp.server.controllers.importer.plugin_api')
@mock.patch('pulp.server.controllers.importer.model')
@mock.patch('pulp.server.controllers.importer.validate_importer_config')
class TestSetImporter(unittest.TestCase):
    """
    Tests for setting an importer on a repository.
    """

    def test_instance_exception(self, m_validate_conf, m_model, m_plug_api, m_clean, *_):
        """
        Test the behavior with the plugin raises an exception.
        """
        mock_imp_inst = mock.MagicMock()
        mock_imp_inst.importer_added.side_effect = MockException
        mock_plugin_config = mock.MagicMock()
        m_plug_api.get_importer_by_id.return_value = (mock_imp_inst, mock_plugin_config)

        self.assertRaises(exceptions.PulpExecutionException, importer.set_importer,
                          mock.MagicMock(repo_id='mock_repo'), 'mock_imp_type', 'm_conf')

    def test_duplicate(self, m_validate_conf, m_model, m_plug_api, m_clean, mock_remove,
                       mock_plug_call_config, *_):
        """
        Ensure that if an importer already exists, it is replaced by the new one.
        """
        mock_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_importer = m_model.Importer.return_value
        mock_imp_inst = mock.MagicMock()
        mock_call_config = mock_plug_call_config.return_value
        mock_remove.side_effect = exceptions.MissingResource
        mock_plugin_config = mock.MagicMock()
        m_plug_api.get_importer_by_id.return_value = (mock_imp_inst, mock_plugin_config)

        result = importer.set_importer('mrepo', 'mtype', 'm_conf')
        m_clean.assert_called_once_with('m_conf')
        mock_plug_call_config.assert_called_once_with(mock_plugin_config, m_clean.return_value)
        mock_remove.assert_called_once_with('mrepo')
        mock_imp_inst.importer_added.assert_called_once_with(mock_repo.to_transfer_repo(),
                                                             mock_call_config)
        mock_importer.save.assert_called_once_with()
        m_model.Importer.SERIALIZER.assert_called_once_with(mock_importer)
        self.assertTrue(result is m_model.Importer.SERIALIZER.return_value.data)

    def test_as_expected(self, m_validate_conf, m_model, m_plug_api, m_clean, mock_remove,
                         mock_plug_call_config, *_):
        """
        Ensure that if an importer does not already exist, it is created.
        """
        mock_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_importer = m_model.Importer.return_value
        mock_imp_inst = mock.MagicMock()
        mock_call_config = mock_plug_call_config.return_value
        mock_plugin_config = mock.MagicMock()
        m_plug_api.get_importer_by_id.return_value = (mock_imp_inst, mock_plugin_config)

        result = importer.set_importer('mrepo', 'mtype', 'm_conf')
        mock_remove.assert_called_once_with('mrepo')
        mock_imp_inst.importer_added.assert_called_once_with(mock_repo.to_transfer_repo(),
                                                             mock_call_config)
        m_clean.assert_called_once_with('m_conf')
        mock_plug_call_config.assert_called_once_with(mock_plugin_config, m_clean.return_value)
        mock_importer.save.assert_called_once_with()
        m_model.Importer.SERIALIZER.assert_called_once_with(mock_importer)
        self.assertTrue(result is m_model.Importer.SERIALIZER.return_value.data)

    def test_validation_error(self, m_validate_conf, m_model, m_plug_api, m_clean, mock_remove,
                              mock_plug_call_config, *_):
        """
        Ensure that if an importer cannot be saved, it raises an InvalidValue.
        """
        mrepo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_importer = m_model.Importer.return_value
        mock_imp_inst = mock.MagicMock()
        mock_importer.save.side_effect = ValidationError(repo_id='invalid')
        mock_call_config = mock_plug_call_config.return_value
        mock_plugin_config = mock.MagicMock()
        m_plug_api.get_importer_by_id.return_value = (mock_imp_inst, mock_plugin_config)

        self.assertRaises(exceptions.InvalidValue, importer.set_importer, 'mrepo', 'mtype', 'mconf')
        m_clean.assert_called_once_with('mconf')
        mock_remove.assert_called_once_with('mrepo')
        mock_imp_inst.importer_added.assert_called_once_with(mrepo.to_transfer_repo(),
                                                             mock_call_config)
        mock_plug_call_config.assert_called_once_with(mock_plugin_config, m_clean.return_value)
        mock_importer.save.assert_called_once_with()

    def test_task_name(self, *_):
        """
        Ensure that the name of the set_importer task matches the historical name for this task.
        """
        self.assertEqual(
            importer.set_importer.name, 'pulp.server.managers.repo.importer.set_importer')


class TestCleanConfigDict(unittest.TestCase):
    """
    Tests for clean config helper.
    """

    def test_as_expected_conf(self):
        """
        Ensure that keys whose value is None are removed.
        """
        mock_config = {'keep': 'this', 'Lose': None, 'Also lose': None, 'also keep': 'this'}
        expected_clean_config = {'keep': 'this', 'also keep': 'this'}
        result = importer.clean_config_dict(mock_config)
        self.assertDictEqual(expected_clean_config, result)

    def test_as_expected_no_trim(self):
        """
        If a config without None values is passed, it is not modified.
        """
        expected_clean_config = {'keep': 'this', 'also keep': 'this'}
        result = importer.clean_config_dict(expected_clean_config)
        self.assertDictEqual(expected_clean_config, result)

    def test_as_expected_none(self):
        """
        If None is passed instead of a config, return None.
        """
        mock_config = None
        result = importer.clean_config_dict(mock_config)
        self.assertTrue(result is None)


@mock.patch('pulp.server.controllers.importer.set_importer')
@mock.patch('pulp.server.controllers.importer.tags')
class TestQueueSetImporter(unittest.TestCase):
    """
    Tests for dispatching a set importer task.
    """

    def test_queued(self, m_tags, m_set):
        """
        Test that the set_importer task is queued correctly.
        """
        repo = model.Repository('m_id')
        result = importer.queue_set_importer(repo, 'm_type', 'm_conf')
        m_task_tags = [m_tags.resource_tag.return_value, m_tags.action_tag.return_value]
        m_set.apply_async_with_reservation.assert_called_once_with(
            m_tags.RESOURCE_REPOSITORY_TYPE, 'm_id', ['m_id', 'm_type'],
            {'repo_plugin_config': 'm_conf'}, tags=m_task_tags)
        self.assertTrue(result is m_set.apply_async_with_reservation.return_value)


@mock.patch('pulp.server.controllers.importer.clean_config_dict')
@mock.patch('pulp.server.controllers.importer.plugin_api')
@mock.patch('pulp.server.controllers.importer.model.Repository')
class TestValidateImporterConfig(unittest.TestCase):
    """
    Tests for ValidateImporterConfig.
    """

    def test_plugin_is_invalid_importer(self, m_repo_model, m_plug_api, m_clean):
        """
        If the plugin_api returns that an importer is invalid, raise.
        """
        m_plug_api.is_valid_importer.return_value = False
        try:
            importer.validate_importer_config('m_id', 'm_type', 'm_conf')
        except exceptions.PulpCodedValidationException, e:
            pass
        else:
            raise AssertionError('PulpCodedValidationException should be raised if importer type '
                                 'is invalid.')
        self.assertEqual(e.error_code.code, 'PLP1008')

    @mock.patch('pulp.server.controllers.importer.PluginCallConfiguration')
    def test_invalid_as_expected_bool(self, m_plug_call_config, m_repo_model, m_plug_api, m_clean):
        """
        Importer instances can return a boolean or a tuple. Test bool only.
        """
        imp_inst = mock.MagicMock()
        m_repo = m_repo_model.objects.get_repo_or_missing_resource.return_value
        m_plug_api.get_importer_by_id.return_value = (imp_inst, 'plug_config')
        imp_inst.validate_config.return_value = False

        self.assertRaises(
            exceptions.PulpCodedValidationException, importer.validate_importer_config,
            'm_id', 'm_type', 'm_conf'
        )
        m_clean.assert_called_once_with('m_conf')
        m_plug_call_config.assert_called_once_with('plug_config', m_clean.return_value)
        imp_inst.validate_config.assert_called_once_with(
            m_repo.to_transfer_repo.return_value, m_plug_call_config.return_value)

    @mock.patch('pulp.server.controllers.importer.PluginCallConfiguration')
    def test_invalid_as_expected_tuple(self, m_plug_call_config, m_repo_model, m_plug_api, m_clean):
        """
        Importer instances can return a boolean or a tuple. Test tuple.
        """
        imp_inst = mock.MagicMock()
        m_repo = m_repo_model.objects.get_repo_or_missing_resource.return_value
        m_plug_api.get_importer_by_id.return_value = (imp_inst, 'plug_config')
        imp_inst.validate_config.return_value = (False, 'm_message')

        try:
            importer.validate_importer_config('m_id', 'm_type', 'm_conf')
        except exceptions.PulpCodedValidationException, e:
            pass
        else:
            raise AssertionError('PulpCodedValidationException should be raised if importer type '
                                 'is invalid.')

        m_clean.assert_called_once_with('m_conf')
        m_plug_call_config.assert_called_once_with('plug_config', m_clean.return_value)
        imp_inst.validate_config.assert_called_once_with(
            m_repo.to_transfer_repo.return_value, m_plug_call_config.return_value)
        self.assertEqual(e.to_dict()['data']['validation_errors'], 'm_message')

    @mock.patch('pulp.server.controllers.importer.PluginCallConfiguration')
    def test_valid_as_expected(self, m_plug_call_config, m_repo_model, m_plug_api, m_clean):
        """
        Test a valid importer.
        """
        imp_inst = mock.MagicMock()
        m_repo = m_repo_model.objects.get_repo_or_missing_resource.return_value
        m_plug_api.get_importer_by_id.return_value = (imp_inst, 'plug_config')
        imp_inst.validate_config.return_value = True

        # No error messages should be raised.
        importer.validate_importer_config('m_id', 'm_type', 'm_conf')

        m_clean.assert_called_once_with('m_conf')
        m_plug_call_config.assert_called_once_with('plug_config', m_clean.return_value)
        imp_inst.validate_config.assert_called_once_with(
            m_repo.to_transfer_repo.return_value, m_plug_call_config.return_value)


@mock.patch('pulp.server.controllers.importer.model')
@mock.patch('pulp.server.controllers.importer.manager_factory')
@mock.patch('pulp.server.controllers.importer.plugin_api')
@mock.patch('pulp.server.controllers.importer.PluginCallConfiguration')
class TestRemoveImporter(unittest.TestCase):
    """
    Tests for removing an importer.
    """

    def test_as_expected(self, m_plug_call, m_plugin_api, m_factory, mock_models):
        """
        Test removing an importer.
        """
        mock_repo = mock_models.Repository.objects.get_repo_or_missing_resource.return_value
        mock_importer = mock_models.Importer.objects.get_or_404.return_value
        m_imp_inst = mock.MagicMock()
        m_plugin_config = mock.MagicMock()
        m_plugin_api.get_importer_by_id.return_value = (m_imp_inst, m_plugin_config)

        importer.remove_importer('foo')

        m_sync = m_factory.repo_sync_schedule_manager.return_value
        m_sync.delete_by_importer_id.assert_called_once_with('foo', mock_importer.importer_type_id)
        m_plug_call.assert_called_once_with(m_plugin_config, mock_importer.config)
        m_imp_inst.importer_removed.assert_called_once_with(
            mock_repo.to_transfer_repo.return_value, m_plug_call.return_value)
        mock_importer.delete.assert_called_once_with()


@mock.patch('pulp.server.controllers.importer.remove_importer')
@mock.patch('pulp.server.controllers.importer.tags')
@mock.patch('pulp.server.controllers.importer.get_valid_importer')
class TestQueueRemoveImporter(unittest.TestCase):
    """
    Tests for dispatching a task to remove an importer.
    """

    def test_as_expected(self, mock_get_imp, mock_tags, mock_rm_importer):
        """
        Dispatch a task as expected.
        """
        result = importer.queue_remove_importer('mock_r', 'mock_type')
        mock_get_imp.assert_called_once_with('mock_r', 'mock_type')
        call_tags = [mock_tags.resource_tag.return_value, mock_tags.resource_tag.return_value,
                     mock_tags.action_tag.return_value]
        mock_rm_importer.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_r', ['mock_r'], tags=call_tags)
        self.assertTrue(result is mock_rm_importer.apply_async_with_reservation.return_value)


@mock.patch('pulp.server.controllers.importer.model')
class TestGetValidImporter(unittest.TestCase):
    """
    Tests for getting an importer given an importer type and repo.
    """

    def test_as_expected(self, mock_model):
        """
        Get an importer with a valid importer_type_id that is associated to the given repo.
        """
        mock_importer = mock_model.Importer.objects.get_or_404.return_value
        result = importer.get_valid_importer('mock_repo', mock_importer.importer_type_id)
        self.assertTrue(result is mock_importer)

    def test_nonexisent_importer(self, mock_model):
        """
        Try to get an importer that doesn't exist.
        """
        mock_model.Importer.objects.get_or_404.side_effect = exceptions.MissingResource('foo')
        try:
            importer.get_valid_importer('mock_repo', 'mock_imp')
        except exceptions.MissingResource, result:
            pass
        else:
            raise AssertionError('MissingResource should be raised when importer does not exist.')

        self.assertDictEqual(result.resources, {'importer_id': 'mock_imp'})

    def test_invalid_importer(self, mock_model):
        """
        Test with an extant importer that is not associated with the given repository.
        """
        mock_importer = mock_model.Importer.objects.get_or_404.return_value
        try:
            importer.get_valid_importer('mock_repo', 'mock_imp')
        except exceptions.MissingResource, result:
            pass
        else:
            raise AssertionError('MissingResource should be raised when importer does not exist.')

        self.assertNotEqual(mock_importer.importer_type_id, 'mock_imp')
        self.assertDictEqual(result.resources, {'importer_id': 'mock_imp'})


@mock.patch('pulp.server.controllers.importer.validate_importer_config')
@mock.patch('pulp.server.controllers.importer.plugin_api')
@mock.patch('pulp.server.controllers.importer.model')
class TestUpdateImporterConfig(unittest.TestCase):
    """
    Tests for updating an importer.
    """

    def test_minimal(self, mock_model, mock_plugin_api, mock_validate_config):
        """
        Update an importer config in the minimal way.
        """
        mock_importer = mock_model.Importer.objects.get_or_404.return_value
        mock_imp_inst = mock.MagicMock()
        mock_plugin_config = mock.MagicMock()
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp_inst, mock_plugin_config)
        mock_ser = mock_model.Importer.SERIALIZER
        mock_validate_config.return_value = (True, 'message')

        result = importer.update_importer_config('mrepo', {'test': 'config'})
        mock_importer.config.update.assert_called_once_with({'test': 'config'})
        mock_importer.save.assert_called_once_with()
        mock_ser.assert_called_once_with(mock_importer)
        self.assertTrue(result is mock_ser.return_value.data)

    def test_unset(self, mock_model, mock_plugin_api, mock_validate_config):
        """
        Test that keys with value None are removed from the config.
        """
        mock_importer = mock_model.Importer.objects.get_or_404.return_value
        mock_importer.config = {'keep': 'keep', 'dont_keep': 'dont_keep'}
        mock_imp_inst = mock.MagicMock()
        mock_plugin_config = mock.MagicMock()
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp_inst, mock_plugin_config)
        mock_ser = mock_model.Importer.SERIALIZER
        mock_validate_config.return_value = (True, 'message')

        result = importer.update_importer_config('mrepo', {'test': 'change', 'dont_keep': None})
        self.assertDictEqual(mock_importer.config, {'test': 'change', 'keep': 'keep'})
        mock_importer.save.assert_called_once_with()
        mock_ser.assert_called_once_with(mock_importer)
        self.assertTrue(result is mock_ser.return_value.data)

    def test_invalid(self, mock_model, mock_plugin_api, mock_validate_config):
        """
        Test behavior if config is invalid.
        """
        mock_importer = mock_model.Importer.objects.get_or_404.return_value
        mock_importer.save.side_effect = ValidationError
        mock_imp_inst = mock.MagicMock()
        mock_plugin_config = mock.MagicMock()
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp_inst, mock_plugin_config)

        self.assertRaises(exceptions.InvalidValue, importer.update_importer_config,
                          'mrepo', {'test': 'config'})


@mock.patch('pulp.server.controllers.importer.update_importer_config')
@mock.patch('pulp.server.controllers.importer.tags')
@mock.patch('pulp.server.controllers.importer.get_valid_importer')
class TestQueueUpdateImporterConfig(unittest.TestCase):
    """
    Tests for dispatching a task to update the importer config.
    """

    def test_as_expected(self, mock_get_imp, mock_tags, mock_update_importer):
        """
        Test dispatching a task to update the importer config.
        """
        result = importer.queue_update_importer_config('mock_r', 'mock_type', 'mock_config')
        mock_get_imp.assert_called_once_with('mock_r', 'mock_type')
        call_tags = [mock_tags.resource_tag.return_value, mock_tags.resource_tag.return_value,
                     mock_tags.action_tag.return_value]
        mock_update_importer.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_r', ['mock_r'],
            {'importer_config': 'mock_config'}, tags=call_tags)
        self.assertTrue(result is mock_update_importer.apply_async_with_reservation.return_value)
