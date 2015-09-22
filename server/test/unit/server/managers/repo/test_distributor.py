import mock

from .... import base
from pulp.devel import mock_plugins
from pulp.plugins.config import PluginCallConfiguration
from pulp.server.db import models
from pulp.server.db.model.repository import RepoDistributor
import pulp.server.exceptions as exceptions
import pulp.server.managers.repo.distributor as distributor_manager


@mock.patch('pulp.server.managers.repo.distributor.models.Repository.objects')
class RepoDistributorManagerTests(base.PulpServerTests):

    def setUp(self):
        super(RepoDistributorManagerTests, self).setUp()
        mock_plugins.install()

        # Create the manager instance to test
        self.distributor_manager = distributor_manager.RepoDistributorManager()

    def tearDown(self):
        super(RepoDistributorManagerTests, self).tearDown()
        mock_plugins.reset()

    def clean(self):
        super(RepoDistributorManagerTests, self).clean()

        mock_plugins.MOCK_DISTRIBUTOR.reset_mock()
        models.Repository.drop_collection()
        RepoDistributor.get_collection().remove()

    def test_add_distributor(self, mock_repo_qs):
        """
        Tests adding a distributor to a new repo.
        """
        mock_repo = mock_repo_qs.get_repo_or_missing_resource()
        config = {'key1': 'value1', 'key2': None}
        added = self.distributor_manager.add_distributor('test_me', 'mock-distributor', config,
                                                         True, distributor_id='my_dist')

        # Verify
        expected_config = {'key1': 'value1'}

        # Database
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(1, len(all_distributors))
        self.assertEqual('my_dist', all_distributors[0]['id'])
        self.assertEqual('mock-distributor', all_distributors[0]['distributor_type_id'])
        self.assertEqual('test_me', all_distributors[0]['repo_id'])
        self.assertEqual(expected_config, all_distributors[0]['config'])
        self.assertTrue(all_distributors[0]['auto_publish'])

        #   Returned Value
        self.assertEqual('my_dist', added['id'])
        self.assertEqual('mock-distributor', added['distributor_type_id'])
        self.assertEqual('test_me', added['repo_id'])
        self.assertEqual(expected_config, added['config'])
        self.assertTrue(added['auto_publish'])

        #   Plugin - Validate Config
        self.assertEqual(1, mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_count)
        call_repo = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][1]

        self.assertTrue(call_repo is mock_repo.to_transfer_repo())

        self.assertTrue(isinstance(call_config, PluginCallConfiguration))
        self.assertTrue(call_config.plugin_config is not None)
        self.assertEqual(call_config.repo_plugin_config, expected_config)

        #   Plugin - Distributor Added
        self.assertEqual(1, mock_plugins.MOCK_DISTRIBUTOR.distributor_added.call_count)
        call_repo = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][1]
        self.assertTrue(call_repo is mock_repo.to_transfer_repo())
        self.assertTrue(isinstance(call_config, PluginCallConfiguration))

    def test_add_distributor_multiple_distributors(self, mock_repo_qs):
        """
        Tests adding a second distributor to a repository.
        """
        self.distributor_manager.add_distributor(
            'test_me', 'mock-distributor', {}, True, distributor_id='dist_1')

        # Test
        self.distributor_manager.add_distributor(
            'test_me', 'mock-distributor-2', {}, True, distributor_id='dist_2')

        # Verify
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(2, len(all_distributors))

        dist_ids = [d['id'] for d in all_distributors]
        self.assertTrue('dist_1' in dist_ids)
        self.assertTrue('dist_2' in dist_ids)

    def test_add_distributor_replace_existing(self, mock_repo_qs):
        """
        Tests adding a distributor under the same ID as an existing distributor.
        """
        self.distributor_manager.add_distributor(
            'test_me', 'mock-distributor', {}, True, distributor_id='dist_1')
        config = {'foo': 'bar'}
        self.distributor_manager.add_distributor('test_me', 'mock-distributor', config, False,
                                                 distributor_id='dist_1')

        # Database
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(1, len(all_distributors))
        self.assertTrue(not all_distributors[0]['auto_publish'])
        self.assertEqual(config, all_distributors[0]['config'])

        # Plugin Calls
        self.assertEqual(2, mock_plugins.MOCK_DISTRIBUTOR.distributor_added.call_count)
        self.assertEqual(1, mock_plugins.MOCK_DISTRIBUTOR.distributor_removed.call_count)

    def test_add_distributor_no_explicit_id(self, mock_repo_qs):
        """
        Tests the ID generation when one is not specified for a distributor.
        """

        added = self.distributor_manager.add_distributor('happy-repo', 'mock-distributor', {}, True)

        # Verify
        distributor = RepoDistributor.get_collection().find_one({'repo_id': 'happy-repo',
                                                                 'id': added['id']})
        self.assertTrue(distributor is not None)

    def test_add_distributor_no_distributor(self, mock_repo_qs):
        """
        Tests adding a distributor that doesn't exist.
        """

        try:
            self.distributor_manager.add_distributor('real-repo', 'fake-distributor', {}, True)
            self.fail('No exception thrown for an invalid distributor type')
        except exceptions.InvalidValue, e:
            self.assertEqual(str(e), "Invalid properties: ['distributor_type_id']")

    def test_add_distributor_invalid_id(self, mock_repo_qs):
        """
        Tests adding a distributor with an invalid ID raises the correct error.
        """

        bad_id = '!@#$%^&*()'
        try:
            self.distributor_manager.add_distributor('repo', 'mock-distributor', {}, True, bad_id)
            self.fail('No exception thrown for an invalid distributor ID')
        except exceptions.InvalidValue, e:
            self.assertTrue('distributor_id' in e.property_names)
            self.assertEqual(str(e), "Invalid properties: ['distributor_id']")

    def test_add_distributor_initialize_raises_error(self, mock_repo_qs):
        """
        Tests the correct error is raised when the distributor raises an error during validation.
        """

        mock_plugins.MOCK_DISTRIBUTOR.distributor_added.side_effect = Exception()

        try:
            self.distributor_manager.add_distributor('repo', 'mock-distributor', {}, True)
            self.fail('Exception expected for error during validate')
        except exceptions.PulpExecutionException:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.distributor_added.side_effect = None

    def test_add_distributor_validate_raises_error(self, mock_repo_qs):
        """
        Tests the correct error is raised when the distributor raises an error during config
        validation.
        """

        mock_plugins.MOCK_DISTRIBUTOR.validate_config.side_effect = Exception()

        try:
            self.distributor_manager.add_distributor('rohan', 'mock-distributor', {}, True)
            self.fail('Exception expected')
        except Exception:
            pass

    def test_add_distributor_invalid_config(self, mock_repo_qs):
        """
        Tests the correct error is raised when the distributor is handed an invalid configuration.
        """

        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = (False, 'Invalid config')

        try:
            self.distributor_manager.add_distributor('error_repo', 'mock-distributor', {}, True)
            self.fail('Exception expected for invalid configuration')
        except exceptions.PulpDataException, e:
            self.assertEqual(e[0], 'Invalid config')

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = True

    def test_add_distributor_invalid_config_backward_compatibility(self, mock_repo_qs):
        """
        Tests the correct error is raised when the distributor is handed an invalid configuration.
        """

        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = False

        try:
            self.distributor_manager.add_distributor('error_repo', 'mock-distributor', {}, True)
            self.fail('Exception expected for invalid configuration')
        except exceptions.PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = True

    @mock.patch(
        'pulp.server.managers.schedule.repo.RepoPublishScheduleManager.delete_by_distributor_id')
    def test_remove_distributor(self, mock_delete_schedules, mock_repo_qs):
        """
        Tests removing an existing distributor from a repository.
        """

        self.distributor_manager.add_distributor(
            'dist-repo', 'mock-distributor', {}, True, distributor_id='doomed')
        self.distributor_manager.remove_distributor('dist-repo', 'doomed')

        # Verify
        distributor = RepoDistributor.get_collection().find_one({'repo_id': 'dist-repo',
                                                                 'id': 'doomed'})
        self.assertTrue(distributor is None)
        mock_delete_schedules.assert_called_once_with('dist-repo', 'doomed')

    def test_remove_distributor_no_distributor(self, mock_repo_qs):
        """
        Tests that no exception is raised when requested to remove a distributor that doesn't exist.
        """

        try:
            self.distributor_manager.remove_distributor('empty', 'non-existent')
        except exceptions.MissingResource, e:
            self.assertTrue('non-existent' == e.resources['distributor'])

    def test_update_distributor_config(self, mock_repo_qs):
        """
        Tests the successful case of updating a distributor's config.
        """

        config = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        distributor = self.distributor_manager.add_distributor('dawnstar', 'mock-distributor',
                                                               config, True)
        dist_id = distributor['id']

        # Test
        delta_config = {'key1': 'updated1', 'key2': None}
        self.distributor_manager.update_distributor_config('dawnstar', dist_id, delta_config)

        # Verify
        expected_config = {'key1': 'updated1', 'key3': 'value3'}

        # Database
        repo_dist = RepoDistributor.get_collection().find_one({'repo_id': 'dawnstar'})
        self.assertEqual(repo_dist['config'], expected_config)

        # Plugin
        self.assertEqual(2, mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_count)
        call_config = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][1]
        self.assertEqual(expected_config, call_config.repo_plugin_config)

    def test_update_auto_publish(self, mock_repo_qs):
        config = {'key': 'value'}
        distributor = self.distributor_manager.add_distributor('test-repo', 'mock-distributor',
                                                               config, True)

        # Test
        self.distributor_manager.update_distributor_config('test-repo', distributor['id'], {},
                                                           False)
        repo_dist = RepoDistributor.get_collection().find_one({'repo_id': 'test-repo'})
        self.assertFalse(repo_dist['auto_publish'])

    def test_update_invalid_auto_publish(self, mock_repo_qs):
        config = {'key': 'value'}
        distributor = self.distributor_manager.add_distributor(
            'test-repo', 'mock-distributor', config, True)

        # Test that an exception is raised if you hand update_distributor_config a bad auto_publish
        self.assertRaises(
            exceptions.InvalidValue, self.distributor_manager.update_distributor_config,
            'test-repo', distributor['id'], {}, 'notbool')

    def test_update_missing_distributor(self, mock_repo_qs):
        """
        Tests updating the config on a distributor that doesn't exist on the repo.
        """

        try:
            self.distributor_manager.update_distributor_config('empty', 'missing', {})
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('missing' == e.resources['distributor'])

    def test_update_validate_exception(self, mock_repo_qs):
        """
        Tests updating a config when the plugin raises an exception during validate.
        """

        distributor = self.distributor_manager.add_distributor('elf', 'mock-distributor', {}, True)
        dist_id = distributor['id']

        class TestException(Exception):
            pass

        mock_plugins.MOCK_DISTRIBUTOR.validate_config.side_effect = TestException()

        self.assertRaises(TestException, self.distributor_manager.update_distributor_config,
                          'elf', dist_id, {})

    def test_update_invalid_config(self, mock_repo_qs):
        """
        Tests updating a config when the plugin indicates the config is invalid.
        """

        distributor = self.distributor_manager.add_distributor(
            'dwarf', 'mock-distributor', {}, True)
        dist_id = distributor['id']

        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = (False, 'Invalid config')

        # Test
        try:
            self.distributor_manager.update_distributor_config('dwarf', dist_id, {})
            self.fail('Exception expected')
        except exceptions.PulpDataException, e:
            self.assertEqual(e[0], 'Invalid config')

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = True

    def test_update_invalid_config_backward_compatibility(self, mock_repo_qs):
        """
        Tests updating a config when the plugin indicates the config is invalid.
        """

        distributor = self.distributor_manager.add_distributor(
            'dwarf', 'mock-distributor', {}, True)
        dist_id = distributor['id']

        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = False

        # Test
        try:
            self.distributor_manager.update_distributor_config('dwarf', dist_id, {})
            self.fail('Exception expected')
        except exceptions.PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = True

    def test_create_bind_payload(self, mock_repo_qs):
        # Setup
        repo_id = 'repo-a'
        distributor_id = 'dist-1'
        binding_config = {'a': 'a'}

        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        self.distributor_manager.add_distributor('repo-a', 'mock-distributor', {}, True,
                                                 distributor_id=distributor_id)

        expected_payload = {'payload': 'stuff'}
        mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.return_value = expected_payload

        # Test
        payload = self.distributor_manager.create_bind_payload(repo_id, distributor_id,
                                                               binding_config)

        # Verify
        self.assertEqual(payload, expected_payload)

        call_args = mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.call_args[0]
        self.assertEqual(call_args[0].id, mock_repo.to_transfer_repo().id)
        self.assertTrue(isinstance(call_args[1], PluginCallConfiguration))
        self.assertEqual(call_args[2], binding_config)

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.return_value = None

    def test_create_bind_payload_distributor_error(self, mock_repo_qs):
        self.distributor_manager.add_distributor('repo-a', 'mock-distributor', {}, True,
                                                 distributor_id='dist-1')

        # This module is doing some very strange things with mock, and this Exception side effect
        # was causing other unrelated tests to fail. Unfortunately, the with operator does not work
        # here due to the call to reset_mock() in the clean() method. This was the only way I could
        # get this to work in reasonable time.
        original_side_effect = mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.side_effect
        try:
            mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.side_effect = Exception()

            # Test
            self.assertRaises(
                exceptions.PulpExecutionException,
                self.distributor_manager.create_bind_payload, 'repo-a', 'dist-1', 'config')
        finally:
            mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.side_effect = original_side_effect

    def test_get_distributor(self, mock_repo_qs):
        """
        Tests the successful case of getting a repo distributor.
        """

        distributor_config = {'element': 'fire'}
        self.distributor_manager.add_distributor('fire', 'mock-distributor', distributor_config,
                                                 True, distributor_id='flame')

        # Test
        distributor = self.distributor_manager.get_distributor('fire', 'flame')

        # Verify
        self.assertTrue(distributor is not None)
        self.assertEqual(distributor['id'], 'flame')
        self.assertEqual(distributor['repo_id'], 'fire')
        self.assertEqual(distributor['config'], distributor_config)

    def test_get_distributor_missing_distributor(self, mock_repo_qs):
        """
        Tests the case of getting a distributor that doesn't exist on a valid repo.
        """

        try:
            self.distributor_manager.get_distributor('empty', 'irrelevant')
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('irrelevant' == e.resources['distributor'])

    def test_get_distributors(self, mock_repo_qs):
        """
        Tests getting all distributors in the normal successful case.
        """

        distributor_config = {'element': 'ice'}
        self.distributor_manager.add_distributor(
            'ice', 'mock-distributor', distributor_config, True, distributor_id='snowball-1')
        self.distributor_manager.add_distributor(
            'ice', 'mock-distributor', distributor_config, True, distributor_id='snowball-2')

        # Test
        distributors = self.distributor_manager.get_distributors('ice')

        # Verify
        self.assertTrue(distributors is not None)
        self.assertEqual(2, len(distributors))

    def test_get_distributors_none(self, mock_repo_qs):
        """
        Tests an empty list is returned when none are present on the repo.
        """

        distributors = self.distributor_manager.get_distributors('empty')
        self.assertTrue(distributors is not None)
        self.assertEqual(0, len(distributors))

    def test_get_set_distributor_scratchpad(self, mock_repo_qs):
        """
        Tests the retrieval and setting of a repo distributor's scratchpad.
        """

        self.distributor_manager.add_distributor(
            'repo', 'mock-distributor', {}, True, distributor_id='dist')

        # Test - Unset Scratchpad
        scratchpad = self.distributor_manager.get_distributor_scratchpad('repo', 'dist')
        self.assertTrue(scratchpad is None)

        # Test - Set
        contents = 'gnomish mines'
        self.distributor_manager.set_distributor_scratchpad('repo', 'dist', contents)

        # Test - Get
        scratchpad = self.distributor_manager.get_distributor_scratchpad('repo', 'dist')
        self.assertEqual(contents, scratchpad)

    def test_get_set_distributor_scratchpad_missing(self, mock_repo_qs):
        """
        Tests no error is raised when getting or setting the scratchpad for missing cases.
        """

        scratchpad = self.distributor_manager.get_distributor_scratchpad('empty', 'not_there')
        self.assertTrue(scratchpad is None)

        # Test - Set No Distributor
        self.distributor_manager.set_distributor_scratchpad('empty', 'fake_distributor', 'stuff')

        # Test - Set No Repo
        self.distributor_manager.set_distributor_scratchpad('fake', 'irrelevant', 'blah')

    def test_publish_schedule(self, mock_repo_qs):

        # setup
        repo_id = 'scheduled_repo'
        distributor_type_id = 'mock-distributor'
        distributor_id = 'scheduled_repo_distributor'
        schedule_id = 'scheduled_repo_publish'
        self.distributor_manager.add_distributor(
            repo_id, distributor_type_id, {}, False, distributor_id=distributor_id)

        # pre-condition
        self.assertEqual(
            len(self.distributor_manager.list_publish_schedules(repo_id, distributor_id)), 0)

        # add the schedule
        self.distributor_manager.add_publish_schedule(repo_id, distributor_id, schedule_id)
        self.assertTrue(
            schedule_id in self.distributor_manager.list_publish_schedules(repo_id, distributor_id))
        self.assertEqual(
            len(self.distributor_manager.list_publish_schedules(repo_id, distributor_id)), 1)

        # idempotent add
        self.distributor_manager.add_publish_schedule(repo_id, distributor_id, schedule_id)
        self.assertEqual(
            len(self.distributor_manager.list_publish_schedules(repo_id, distributor_id)), 1)

        # remove the schedule
        self.distributor_manager.remove_publish_schedule(repo_id, distributor_id, schedule_id)
        self.assertFalse(
            schedule_id in self.distributor_manager.list_publish_schedules(repo_id, distributor_id))
        self.assertEqual(
            len(self.distributor_manager.list_publish_schedules(repo_id, distributor_id)), 0)

        # idempotent remove
        self.distributor_manager.remove_publish_schedule(repo_id, distributor_id, schedule_id)
        self.assertEqual(
            len(self.distributor_manager.list_publish_schedules(repo_id, distributor_id)), 0)

        # errors
        self.distributor_manager.remove_distributor(repo_id, distributor_id)
        self.assertRaises(exceptions.MissingResource,
                          self.distributor_manager.add_publish_schedule,
                          repo_id, distributor_id, schedule_id)
        self.assertRaises(exceptions.MissingResource,
                          self.distributor_manager.remove_publish_schedule,
                          repo_id, distributor_id, schedule_id)

    @mock.patch.object(RepoDistributor, 'get_collection')
    def test_find_by_repo_list(self, mock_get_collection, mock_repo_qs):
        EXPECT = {'repo_id': {'$in': ['repo-1']}}
        PROJECTION = {'scratchpad': 0}
        self.distributor_manager.find_by_repo_list(['repo-1'])
        self.assertTrue(mock_get_collection.return_value.find.called)
        mock_get_collection.return_value.find.assert_called_once_with(EXPECT, PROJECTION)

    @mock.patch.object(RepoDistributor, 'get_collection')
    def test_find_by_criteria(self, get_collection, mock_repo_qs):
        criteria = mock.Mock()
        collection = mock.Mock()
        get_collection.return_value = collection

        # test
        result = self.distributor_manager.find_by_criteria(criteria)

        # validation
        get_collection.assert_called_once_with()
        collection.query.assert_called_once_with(criteria)
        self.assertEqual(result, collection.query.return_value)
