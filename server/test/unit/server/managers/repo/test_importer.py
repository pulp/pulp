import mock

from .... import base
from pulp.devel import mock_plugins
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.importer import Importer
from pulp.plugins.loader import api as plugin_api
from pulp.server.db import model
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.db.model.repository import RepoImporter
import pulp.server.exceptions as exceptions
import pulp.server.managers.repo.importer as importer_manager


@mock.patch('pulp.server.managers.repo.importer.model.Repository.objects')
class RepoManagerTests(base.PulpServerTests):

    def setUp(self):
        super(RepoManagerTests, self).setUp()
        mock_plugins.install()
        self.importer_manager = importer_manager.RepoImporterManager()

    def tearDown(self):
        super(RepoManagerTests, self).tearDown()
        mock_plugins.reset()

    def clean(self):
        super(RepoManagerTests, self).clean()
        model.Repository.drop_collection()
        RepoImporter.get_collection().remove()

    def test_set_importer(self, mock_repo_qs):
        """
        Tests setting an importer on a new repo (normal case).
        """
        mock_repo = mock_repo_qs.get_repo_or_missing_resource()
        importer_config = {'key1': 'value1', 'key2': None}

        # Test
        created = self.importer_manager.set_importer(
            'importer-test', 'mock-importer', importer_config)

        # Verify
        expected_config = {'key1': 'value1'}

        # Database
        importer = RepoImporter.get_collection().find_one(
            {'repo_id': 'importer-test', 'id': 'mock-importer'})
        self.assertEqual('importer-test', importer['repo_id'])
        self.assertEqual('mock-importer', importer['id'])
        self.assertEqual('mock-importer', importer['importer_type_id'])
        self.assertEqual(expected_config, importer['config'])

        #   Return Value
        self.assertEqual('importer-test', created['repo_id'])
        self.assertEqual('mock-importer', created['id'])
        self.assertEqual('mock-importer', created['importer_type_id'])
        self.assertEqual(expected_config, created['config'])

        #   Plugin - Validate Config
        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.importer_added.call_count)
        call_repo = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][1]

        self.assertTrue(call_repo is mock_repo.to_transfer_repo())

        self.assertTrue(isinstance(call_config, PluginCallConfiguration))
        self.assertTrue(call_config.plugin_config is not None)
        self.assertEqual(call_config.repo_plugin_config, expected_config)

        #   Plugin - Importer Added
        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.validate_config.call_count)
        call_repo = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][1]
        self.assertTrue(call_repo is mock_repo.to_transfer_repo())
        self.assertTrue(isinstance(call_config, PluginCallConfiguration))

    def test_set_importer_no_importer(self, mock_repo_qs):
        """
        Tests setting an importer that doesn't exist on a repo.
        """
        self.assertRaises(exceptions.PulpCodedValidationException,
                          self.importer_manager.set_importer, 'real-repo', 'fake-importer', None)

    def test_set_importer_with_existing(self, mock_repo_qs):
        """
        Tests setting a different importer on a repo that already had one.
        """

        class MockImporter2(Importer):
            @classmethod
            def metadata(cls):
                return {'types': ['mock_types_2']}

            def validate_config(self, repo_data, importer_config):
                return True

        mock_plugins.IMPORTER_MAPPINGS['mock-importer-2'] = MockImporter2()
        plugin_api._MANAGER.importers.add_plugin('mock-importer-2', MockImporter2, {})

        self.importer_manager.set_importer('change_me', 'mock-importer', {})

        # Test
        self.importer_manager.set_importer('change_me', 'mock-importer-2', {})

        # Verify
        all_importers = list(RepoImporter.get_collection().find())
        self.assertEqual(1, len(all_importers))
        self.assertEqual(all_importers[0]['id'], 'mock-importer-2')

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.importer_removed.call_count)
        RepoImporter.get_collection().remove()

    def test_set_importer_added_raises_error(self, mock_repo_qs):
        """
        Tests simulating an error coming out of the importer's validate config method.
        """
        mock_plugins.MOCK_IMPORTER.importer_added.side_effect = Exception()
        config = {'hobbit': 'frodo'}

        try:
            self.importer_manager.set_importer('repo-1', 'mock-importer', config)
            self.fail('Exception expected for importer plugin exception')
        except exceptions.PulpExecutionException:
            pass
        finally:
            mock_plugins.MOCK_IMPORTER.importer_added.side_effect = None
            RepoImporter.get_collection().remove()

    def test_set_importer_validate_config_error(self, mock_repo_qs):
        """
        Tests manager handling when the plugin raises an error while validating a config.
        """
        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = IOError()
        self.assertRaises(IOError, self.importer_manager.set_importer, 'bad_config',
                          'mock-importer', {})
        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = None

    def test_set_importer_invalid_config(self, mock_repo_qs):
        """
        Tests the set_importer call properly errors when the config is invalid.
        """
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = (False, 'Invalid stuff')
        config = {'elf': 'legolas'}
        self.assertRaises(exceptions.PulpCodedValidationException,
                          self.importer_manager.set_importer, 'bad_config', 'mock-importer', config)

    def test_set_importer_invalid_config_backward_compatibility(self, mock_repo_qs):
        """
        Tests the set_importer call properly errors when the config is invalid
        and the importer still returns a single boolean.
        """
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = False
        config = {'elf': 'legolas'}
        self.assertRaises(exceptions.PulpCodedValidationException,
                          self.importer_manager.set_importer, 'bad_config', 'mock-importer', config)

    @mock.patch('pulp.plugins.loader.api.is_valid_importer', return_value=False)
    @mock.patch('pulp.server.db.model.base.Model.get_collection')
    def test_validate_importer_config_no_importer(self, mock_get_collection,
                                                  mock_importer_validator, mock_repo_model):
        """
        Test that the validator raises a PulpCodedValidationException if the importer doesn't exist
        """
        self.assertRaises(exceptions.PulpCodedValidationException,
                          self.importer_manager.validate_importer_config, 'repo', 'importer_id', {})
        mock_importer_validator.assert_called_once_with('importer_id')

    @mock.patch('pulp.plugins.loader.api.is_valid_importer', return_value=True)
    @mock.patch('pulp.plugins.loader.api.get_importer_by_id')
    def test_validate_importer_config_invalid_config(self, mock_get_importer, *unused_mocks):
        mock_importer = mock.Mock()
        mock_importer.validate_config.return_value = (False, 'What are exceptions?')
        mock_get_importer.return_value = (mock_importer, {})

        self.assertRaises(exceptions.PulpCodedValidationException,
                          self.importer_manager.validate_importer_config, 'repo', 'importer_id',
                          {'sweep_it_up': None})

        self.assertEqual(1, mock_importer.validate_config.call_count)
        config = mock_importer.validate_config.call_args[0][1]
        self.assertEqual({}, config.plugin_config)
        self.assertEqual({}, config.repo_plugin_config)

    @mock.patch('pulp.server.managers.schedule.repo.RepoSyncScheduleManager.delete_by_importer_id')
    def test_remove_importer(self, mock_delete_schedules, mock_repo_qs):
        """
        Tests the successful case of removing an importer.
        """
        self.importer_manager.set_importer('whiterun', 'mock-importer', {})
        importer = RepoImporter.get_collection().find_one({'repo_id': 'whiterun',
                                                           'id': 'mock-importer'})
        self.assertTrue(importer is not None)
        self.importer_manager.remove_importer('whiterun')
        importer = RepoImporter.get_collection().find_one({'repo_id': 'whiterun',
                                                           'id': 'mock-importer'})
        self.assertTrue(importer is None)

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.importer_removed.call_count)
        mock_delete_schedules.assert_called_once_with('whiterun', 'mock-importer')

    def test_remove_importer_missing_importer(self, mock_repo_qs):
        """
        Tests removing an importer from a repo that doesn't have one.
        """
        try:
            self.importer_manager.remove_importer('solitude')
            self.fail('Exception expected')
        except exceptions.MissingResource:
            pass

    @mock.patch('pulp.server.managers.repo.importer.serializers.ImporterSerializer')
    def test_update_importer_config(self, m_serializer, mock_repo_qs):
        """
        Tests the successful case of updating an importer's configuration.
        """
        orig_config = {'key1': 'initial1', 'key2': 'initial2', 'key3': 'initial3'}
        self.importer_manager.set_importer('winterhold', 'mock-importer', orig_config)
        config_delta = {'key1': 'updated1', 'key2': None}

        self.importer_manager.update_importer_config('winterhold', config_delta)
        expected_config = {'key1': 'updated1', 'key3': 'initial3'}
        set_config = m_serializer.mock_calls[0][1][0]['config']
        self.assertDictEqual(set_config, expected_config)

        # Database
        importer = RepoImporter.get_collection().find_one(
            {'repo_id': 'winterhold', 'id': 'mock-importer'})
        self.assertEqual(importer['config'], expected_config)

        # Plugin
        # initial and update
        self.assertEqual(2, mock_plugins.MOCK_IMPORTER.validate_config.call_count)
        # returns args from last call
        self.assertEqual(
            expected_config,
            mock_plugins.MOCK_IMPORTER.validate_config.call_args[0][1].repo_plugin_config)

    def test_update_importer_missing_importer(self, mock_repo_qs):
        """
        Tests the appropriate exception is raised when updating a repo that has no importer.
        """
        try:
            self.importer_manager.update_importer_config('empty', {})
            self.fail('Exception expected')
        except exceptions.MissingResource:
            pass

    def test_update_importer_plugin_exception(self, mock_repo_qs):
        """
        Tests the appropriate exception is raised when the plugin throws an error during validation.
        """
        self.importer_manager.set_importer('riverwood', 'mock-importer', {})
        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = Exception()
        try:
            self.importer_manager.update_importer_config('riverwood', {})
            self.fail('Exception expected')
        except exceptions.PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.side_effect = None

    def test_update_importer_invalid_config(self, mock_repo_qs):
        """
        Tests the appropriate exception is raised when the plugin indicates the config is invalid.
        """
        self.importer_manager.set_importer('restoration', 'mock-importer', {})
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = (False, 'Invalid stuff')
        try:
            self.importer_manager.update_importer_config('restoration', {})
            self.fail('Exception expected')
        except exceptions.PulpDataException, e:
            self.assertEqual('Invalid stuff', e[0])

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = True

    def test_update_importer_invalid_config_backward_compatibility(self, mock_repo_qs):
        """
        Tests the appropriate exception is raised when the plugin indicates the config is invalid.
        """
        self.importer_manager.set_importer('restoration', 'mock-importer', {})
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = False
        try:
            self.importer_manager.update_importer_config('restoration', {})
            self.fail('Exception expected')
        except exceptions.PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.validate_config.return_value = True

    def test_get_importer(self, mock_repo_qs):
        """
        Tests retrieving a repo's importer in the successful case.
        """
        importer_config = {'volume': 'two', 'proxy_password': 'secret',
                           'basic_auth_password': 'secret'}
        self.importer_manager.set_importer('trance', 'mock-importer', importer_config)
        importer = self.importer_manager.get_importer('trance')

        # Verify
        self.assertTrue(importer is not None)
        self.assertEqual(importer['id'], 'mock-importer')
        self.assertEqual(importer['repo_id'], 'trance')
        self.assertEqual(importer['config']['volume'], 'two')
        self.assertEqual(importer['config']['proxy_password'], 'secret')
        self.assertEqual(importer['config']['basic_auth_password'], 'secret')

    def test_get_importer_missing_importer(self, mock_repo_qs):
        """
        Tests getting the importer for a repo that doesn't have one associated.
        """
        self.assertRaises(exceptions.MissingResource, self.importer_manager.get_importer, 'empty')

    def test_get_importers(self, mock_repo_qs):
        """
        Tests the successful case of getting the importer list for a repo.
        """
        self.importer_manager.set_importer('trance', 'mock-importer', {})
        importers = self.importer_manager.get_importers('trance')
        self.assertTrue(importers is not None)
        self.assertEqual(1, len(importers))
        self.assertEqual('mock-importer', importers[0]['id'])

    def test_get_importers_none(self, mock_repo_qs):
        """
        Tests an empty list is returned for a repo that has none.
        """
        importers = self.importer_manager.get_importers('trance')
        self.assertTrue(importers is not None)
        self.assertEqual(0, len(importers))

    def test_get_set_importer_scratchpad(self, mock_repo_qs):
        """
        Tests the retrieval and setting of a repo importer's scratchpad.
        """
        self.importer_manager.set_importer('repo', 'mock-importer', {})

        # Test - Unset Scratchpad
        scratchpad = self.importer_manager.get_importer_scratchpad('repo')
        self.assertTrue(scratchpad is None)

        # Test - Set
        contents = ['yendor', 'sokoban']
        self.importer_manager.set_importer_scratchpad('repo', contents)

        # Test - Get
        scratchpad = self.importer_manager.get_importer_scratchpad('repo')
        self.assertEqual(contents, scratchpad)

    def test_get_set_importer_scratchpad_missing(self, mock_repo_qs):
        """
        Tests no error is raised when getting or setting the scratchpad for missing cases.
        """
        scratchpad = self.importer_manager.get_importer_scratchpad('empty')
        self.assertTrue(scratchpad is None)
        self.importer_manager.set_importer_scratchpad('empty', 'foo')  # should not error
        self.importer_manager.set_importer_scratchpad('fake', 'bar')  # should not error

    @mock.patch.object(RepoImporter, 'get_collection')
    def test_find_by_repo_list(self, mock_get_collection, mock_repo_qs):
        EXPECT = {'repo_id': {'$in': ['repo-1']}}
        PROJECTION = {'scratchpad': 0}
        self.importer_manager.find_by_repo_list(['repo-1'])
        self.assertTrue(mock_get_collection.return_value.find.called)
        mock_get_collection.return_value.find.assert_called_once_with(EXPECT, PROJECTION)

    @mock.patch.object(ScheduledCall, 'get_collection')
    def test_find_by_repo_list_no_scheduled_sync(self, mock_get_collection, mock_repo_qs):
        self.importer_manager.find_by_repo_list(['repo-1'])
        self.assertFalse(mock_get_collection.return_value.find.called)
