#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import base
import mock_plugins

from pulp.plugins.model import Repository
from pulp.plugins.config import PluginCallConfiguration
from pulp.server.db.model.repository import Repo, RepoDistributor
import pulp.server.exceptions as exceptions
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.distributor as distributor_manager

# -- test cases ---------------------------------------------------------------

class RepoManagerTests(base.PulpServerTests):

    def setUp(self):
        super(RepoManagerTests, self).setUp()
        mock_plugins.install()

        # Create the manager instance to test
        self.repo_manager = repo_manager.RepoManager()
        self.distributor_manager = distributor_manager.RepoDistributorManager()

    def tearDown(self):
        super(RepoManagerTests, self).tearDown()
        mock_plugins.reset()

    def clean(self):
        super(RepoManagerTests, self).clean()

        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()

    # -- add ------------------------------------------------------------------

    def test_add_distributor(self):
        """
        Tests adding a distributor to a new repo.
        """

        # Setup
        self.repo_manager.create_repo('test_me')
        config = {'key1' : 'value1', 'key2' : None}

        # Test
        added = self.distributor_manager.add_distributor('test_me', 'mock-distributor', config, True, distributor_id='my_dist')

        # Verify
        expected_config = {'key1' : 'value1'}

        #    Database
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

        self.assertTrue(isinstance(call_repo, Repository))
        self.assertEqual('test_me', call_repo.id)

        self.assertTrue(isinstance(call_config, PluginCallConfiguration))
        self.assertTrue(call_config.plugin_config is not None)
        self.assertEqual(call_config.repo_plugin_config, expected_config)

        #   Plugin - Distributor Added
        self.assertEqual(1, mock_plugins.MOCK_DISTRIBUTOR.distributor_added.call_count)
        call_repo = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][1]
        self.assertTrue(isinstance(call_repo, Repository))
        self.assertTrue(isinstance(call_config, PluginCallConfiguration))

    def test_add_distributor_multiple_distributors(self):
        """
        Tests adding a second distributor to a repository.
        """

        self.repo_manager.create_repo('test_me')
        self.distributor_manager.add_distributor('test_me', 'mock-distributor', {}, True, distributor_id='dist_1')

        # Test
        self.distributor_manager.add_distributor('test_me', 'mock-distributor-2', {}, True, distributor_id='dist_2')

        # Verify
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(2, len(all_distributors))

        dist_ids = [d['id'] for d in all_distributors]
        self.assertTrue('dist_1' in dist_ids)
        self.assertTrue('dist_2' in dist_ids)

    def test_add_distributor_replace_existing(self):
        """
        Tests adding a distributor under the same ID as an existing distributor.
        """

        # Setup
        self.repo_manager.create_repo('test_me')

        self.distributor_manager.add_distributor('test_me', 'mock-distributor', {}, True, distributor_id='dist_1')

        # Test
        config = {'foo' : 'bar'}
        self.distributor_manager.add_distributor('test_me', 'mock-distributor', config, False, distributor_id='dist_1')

        # Verify

        #    Database
        all_distributors = list(RepoDistributor.get_collection().find())
        self.assertEqual(1, len(all_distributors))
        self.assertTrue(not all_distributors[0]['auto_publish'])
        self.assertEqual(config, all_distributors[0]['config'])

        #    Plugin Calls
        self.assertEqual(2, mock_plugins.MOCK_DISTRIBUTOR.distributor_added.call_count)
        self.assertEqual(1, mock_plugins.MOCK_DISTRIBUTOR.distributor_removed.call_count)

    def test_add_distributor_no_explicit_id(self):
        """
        Tests the ID generation when one is not specified for a distributor.
        """

        # Setup
        self.repo_manager.create_repo('happy-repo')

        # Test
        added = self.distributor_manager.add_distributor('happy-repo', 'mock-distributor', {}, True)

        # Verify
        distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'happy-repo', 'id' : added['id']})
        self.assertTrue(distributor is not None)

    def test_add_distributor_no_repo(self):
        """
        Tests adding a distributor to a repo that doesn't exist.
        """

        # Test
        try:
            self.distributor_manager.add_distributor('fake', 'mock-distributor', {}, True)
            self.fail('No exception thrown for an invalid repo ID')
        except exceptions.MissingResource, e:
            self.assertTrue('fake' == e.resources['resource_id'])
            print(e) # for coverage

    def test_add_distributor_no_distributor(self):
        """
        Tests adding a distributor that doesn't exist.
        """

        # Setup
        self.repo_manager.create_repo('real-repo')

        # Test
        try:
            self.distributor_manager.add_distributor('real-repo', 'fake-distributor', {}, True)
            self.fail('No exception thrown for an invalid distributor type')
        except exceptions.InvalidValue, e:
            print(e) # for coverage

    def test_add_distributor_invalid_id(self):
        """
        Tests adding a distributor with an invalid ID raises the correct error.
        """

        # Setup
        self.repo_manager.create_repo('repo')

        # Test
        bad_id = '!@#$%^&*()'
        try:
            self.distributor_manager.add_distributor('repo', 'mock-distributor', {}, True, bad_id)
            self.fail('No exception thrown for an invalid distributor ID')
        except exceptions.InvalidValue, e:
            self.assertTrue('distributor_id' in e.property_names)
            print(e) # for coverage

    def test_add_distributor_initialize_raises_error(self):
        """
        Tests the correct error is raised when the distributor raises an error during validation.
        """

        # Setup
        mock_plugins.MOCK_DISTRIBUTOR.distributor_added.side_effect = Exception()
        self.repo_manager.create_repo('repo')

        # Test
        try:
            self.distributor_manager.add_distributor('repo', 'mock-distributor', {}, True)
            self.fail('Exception expected for error during validate')
        except exceptions.PulpExecutionException:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.distributor_added.side_effect = None

    def test_add_distributor_validate_raises_error(self):
        """
        Tests the correct error is raised when the distributor raises an error during config validation.
        """

        # Setup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.side_effect = Exception()
        self.repo_manager.create_repo('rohan')

        # Test
        try:
            self.distributor_manager.add_distributor('rohan', 'mock-distributor', {}, True)
            self.fail('Exception expected')
        except exceptions.PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.side_effect = None

    def test_add_distributor_invalid_config(self):
        """
        Tests the correct error is raised when the distributor is handed an invalid configuration.
        """

        # Setup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = (False, 'Invalid config')
        self.repo_manager.create_repo('error_repo')

        # Test
        try:
            self.distributor_manager.add_distributor('error_repo', 'mock-distributor', {}, True)
            self.fail('Exception expected for invalid configuration')
        except exceptions.PulpDataException, e:
            self.assertEqual(e[0], 'Invalid config')

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = True

    def test_add_distributor_invalid_config_backward_compatibility(self):
        """
        Tests the correct error is raised when the distributor is handed an invalid configuration.
        """

        # Setup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = False
        self.repo_manager.create_repo('error_repo')

        # Test
        try:
            self.distributor_manager.add_distributor('error_repo', 'mock-distributor', {}, True)
            self.fail('Exception expected for invalid configuration')
        except exceptions.PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.return_value = True

    def test_add_distributor_with_related(self):
        # Setup
        self.repo_manager.create_repo('repo-a')
        self.repo_manager.create_repo('repo-b')

        self.distributor_manager.add_distributor('repo-a', 'mock-distributor', {'a1' : 'a1'}, True, distributor_id='dist-a1')
        self.distributor_manager.add_distributor('repo-a', 'mock-distributor', {'a2' : 'a2'}, True, distributor_id='dist-a2')

        # Test
        self.distributor_manager.add_distributor('repo-b', 'mock-distributor', {'b' : 'b'}, True)

        # Verify
        args = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0]
        self.assertEqual(args[1].repo_plugin_config, {'b' : 'b'})

        related_repos = args[2]
        self.assertEqual(1, len(related_repos))
        self.assertEqual(related_repos[0].id, 'repo-a')
        self.assertEqual(2, len(related_repos[0].plugin_configs))
        self.assertTrue({'a1' : 'a1'} in related_repos[0].plugin_configs)
        self.assertTrue({'a2' : 'a2'} in related_repos[0].plugin_configs)

    # -- remove ---------------------------------------------------------------

    def test_remove_distributor(self):
        """
        Tests removing an existing distributor from a repository.
        """

        # Setup
        self.repo_manager.create_repo('dist-repo')
        self.distributor_manager.add_distributor('dist-repo', 'mock-distributor', {}, True, distributor_id='doomed')

        # Test
        self.distributor_manager.remove_distributor('dist-repo', 'doomed')

        # Verify
        distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'dist-repo', 'id' : 'doomed'})
        self.assertTrue(distributor is None)

    def test_remove_distributor_no_distributor(self):
        """
        Tests that no exception is raised when requested to remove a distributor that doesn't exist.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        try:
            self.distributor_manager.remove_distributor('empty', 'non-existent')
        except exceptions.MissingResource, e:
            self.assertTrue('non-existent' == e.resources['resource_id'])

    def test_remove_distributor_no_repo(self):
        """
        Tests the proper exception is raised when removing a distributor from a repo that doesn't exist.
        """

        # Test
        try:
            self.distributor_manager.remove_distributor('fake-repo', 'irrelevant')
            self.fail('No exception thrown for an invalid repo ID')
        except exceptions.MissingResource, e:
            self.assertTrue('fake-repo' == e.resources['resource_id'])
            print(e) # for coverage

    # -- update ---------------------------------------------------------------

    def test_update_distributor_config(self):
        """
        Tests the successful case of updating a distributor's config.
        """

        # Setup
        self.repo_manager.create_repo('dawnstar')
        config = {'key1' : 'value1',
                  'key2' : 'value2',
                  'key3' : 'value3',}
        distributor = self.distributor_manager.add_distributor('dawnstar', 'mock-distributor', config, True)
        dist_id = distributor['id']

        # Test
        delta_config = {'key1' : 'updated1',
                        'key2' : None}
        self.distributor_manager.update_distributor_config('dawnstar', dist_id, delta_config)

        # Verify
        expected_config = {'key1' : 'updated1', 'key3' : 'value3'}

        #    Database
        repo_dist = RepoDistributor.get_collection().find_one({'repo_id' : 'dawnstar'})
        self.assertEqual(repo_dist['config'], expected_config)

        #    Plugin
        self.assertEqual(2, mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_count)
        call_config = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0][1]
        self.assertEqual(expected_config, call_config.repo_plugin_config)

    def test_update_missing_repo(self):
        """
        Tests updating the distributor config on a repo that doesn't exist.
        """

        # Test
        try:
            self.distributor_manager.update_distributor_config('not-there', 'doesnt-matter', {})
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('not-there' == e.resources['resource_id'])

    def test_update_missing_distributor(self):
        """
        Tests updating the config on a distributor that doesn't exist on the repo.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        try:
            self.distributor_manager.update_distributor_config('empty', 'missing', {})
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('missing' == e.resources['resource_id'])

    def test_update_validate_exception(self):
        """
        Tests updating a config when the plugin raises an exception during validate.
        """

        # Setup
        self.repo_manager.create_repo('elf')
        distributor = self.distributor_manager.add_distributor('elf', 'mock-distributor', {}, True)
        dist_id = distributor['id']

        mock_plugins.MOCK_DISTRIBUTOR.validate_config.side_effect = Exception()

        # Test
        try:
            self.distributor_manager.update_distributor_config('elf', dist_id, {})
            self.fail('Exception expected')
        except exceptions.PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.validate_config.side_effect = None

    def test_update_invalid_config(self):
        """
        Tests updating a config when the plugin indicates the config is invalid.
        """

        # Setup
        self.repo_manager.create_repo('dwarf')
        distributor = self.distributor_manager.add_distributor('dwarf', 'mock-distributor', {}, True)
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

    def test_update_invalid_config_backward_compatibility(self):
        """
        Tests updating a config when the plugin indicates the config is invalid.
        """

        # Setup
        self.repo_manager.create_repo('dwarf')
        distributor = self.distributor_manager.add_distributor('dwarf', 'mock-distributor', {}, True)
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

    def test_update_config_with_related(self):
        # Setup
        self.repo_manager.create_repo('repo-a')
        self.repo_manager.create_repo('repo-b')

        self.distributor_manager.add_distributor('repo-a', 'mock-distributor', {'a1' : 'a1'}, True, distributor_id='dist-a1')
        self.distributor_manager.add_distributor('repo-a', 'mock-distributor', {'a2' : 'a2'}, True, distributor_id='dist-a2')
        self.distributor_manager.add_distributor('repo-b', 'mock-distributor', {'b' : 'b'}, True, distributor_id='dist-b')

        # Test
        self.distributor_manager.update_distributor_config('repo-b', 'dist-b', {'b' : 'b2'})

        # Verify
        args = mock_plugins.MOCK_DISTRIBUTOR.validate_config.call_args[0]
        self.assertEqual(args[1].repo_plugin_config, {'b' : 'b2'})

        related_repos = args[2]
        self.assertEqual(1, len(related_repos))
        self.assertEqual(related_repos[0].id, 'repo-a')
        self.assertEqual(2, len(related_repos[0].plugin_configs))
        self.assertTrue({'a1' : 'a1'} in related_repos[0].plugin_configs)
        self.assertTrue({'a2' : 'a2'} in related_repos[0].plugin_configs)

    # -- payload --------------------------------------------------------------

    def test_create_bind_payload(self):
        # Setup
        self.repo_manager.create_repo('repo-a')
        self.distributor_manager.add_distributor('repo-a', 'mock-distributor', {}, True, distributor_id='dist-1')

        expected_payload = {'payload' : 'stuff'}
        mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.return_value = expected_payload

        # Test
        payload = self.distributor_manager.create_bind_payload('repo-a', 'dist-1')

        # Verify
        self.assertEqual(payload, expected_payload)

        # Cleanup
        mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.return_value = None

    def test_create_bind_payload_missing_repo(self):
        # Test
        self.assertRaises(exceptions.MissingResource, self.distributor_manager.create_bind_payload, 'missing', 'also missing')

    def test_create_bind_payload_distributor_error(self):
        # Setup
        self.repo_manager.create_repo('repo-a')
        self.distributor_manager.add_distributor('repo-a', 'mock-distributor', {}, True, distributor_id='dist-1')

        mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.side_effect = Exception()

        # Test
        self.assertRaises(exceptions.PulpExecutionException, self.distributor_manager.create_bind_payload, 'repo-a', 'dist-1')

    # -- get ------------------------------------------------------------------

    def test_get_distributor(self):
        """
        Tests the successful case of getting a repo distributor.
        """

        # Setup
        self.repo_manager.create_repo('fire')
        distributor_config = {'element' : 'fire'}
        self.distributor_manager.add_distributor('fire', 'mock-distributor', distributor_config, True, distributor_id='flame')

        # Test
        distributor = self.distributor_manager.get_distributor('fire', 'flame')

        # Verify
        self.assertTrue(distributor is not None)
        self.assertEqual(distributor['id'], 'flame')
        self.assertEqual(distributor['repo_id'], 'fire')
        self.assertEqual(distributor['config'], distributor_config)

    def test_get_distributor_missing_repo(self):
        """
        Tests the case of getting a distributor for a repo that doesn't exist.
        """

        # Test
        try:
            self.distributor_manager.get_distributor('fake', 'irrelevant')
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('irrelevant' == e.resources['resource_id'])

    def test_get_distributor_missing_distributor(self):
        """
        Tests the case of getting a distributor that doesn't exist on a valid repo.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        try:
            self.distributor_manager.get_distributor('empty', 'irrelevant')
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('irrelevant' == e.resources['resource_id'])

    def test_get_distributors(self):
        """
        Tests getting all distributors in the normal successful case.
        """

        # Setup
        self.repo_manager.create_repo('ice')
        distributor_config = {'element' : 'ice'}
        self.distributor_manager.add_distributor('ice', 'mock-distributor', distributor_config, True, distributor_id='snowball-1')
        self.distributor_manager.add_distributor('ice', 'mock-distributor', distributor_config, True, distributor_id='snowball-2')

        # Test
        distributors = self.distributor_manager.get_distributors('ice')

        # Verify
        self.assertTrue(distributors is not None)
        self.assertEqual(2, len(distributors))

    def test_get_distributors_none(self):
        """
        Tests an empty list is returned when none are present on the repo.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test
        distributors = self.distributor_manager.get_distributors('empty')

        # Verify
        self.assertTrue(distributors is not None)
        self.assertEqual(0, len(distributors))

    def test_get_distributors_missing_repo(self):
        """
        Tests the proper error is raised when getting distributors on a repo that doesn't exist.
        """

        # Test
        try:
            self.distributor_manager.get_distributors('fake')
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('fake' == e.resources['resource_id'])

    # -- scratchpad -----------------------------------------------------------

    def test_get_set_distributor_scratchpad(self):
        """
        Tests the retrieval and setting of a repo distributor's scratchpad.
        """

        # Setup
        self.repo_manager.create_repo('repo')
        self.distributor_manager.add_distributor('repo', 'mock-distributor', {}, True, distributor_id='dist')

        # Test - Unset Scratchpad
        scratchpad = self.distributor_manager.get_distributor_scratchpad('repo', 'dist')
        self.assertTrue(scratchpad is None)

        # Test - Set
        contents = 'gnomish mines'
        self.distributor_manager.set_distributor_scratchpad('repo', 'dist', contents)

        # Test - Get
        scratchpad = self.distributor_manager.get_distributor_scratchpad('repo', 'dist')
        self.assertEqual(contents, scratchpad)

    def test_get_set_distributor_scratchpad_missing(self):
        """
        Tests no error is raised when getting or setting the scratchpad for missing cases.
        """

        # Setup
        self.repo_manager.create_repo('empty')

        # Test - Get
        scratchpad = self.distributor_manager.get_distributor_scratchpad('empty', 'not_there')
        self.assertTrue(scratchpad is None)

        # Test - Set No Distributor
        self.distributor_manager.set_distributor_scratchpad('empty', 'fake_distributor', 'stuff')

        # Test - Set No Repo
        self.distributor_manager.set_distributor_scratchpad('fake', 'irrelevant', 'blah')

    # -- publish schedules -----------------------------------------------------

    def test_publish_schedule(self):

        # setup
        repo_id = 'scheduled_repo'
        distributor_type_id = 'mock-distributor'
        distributor_id = 'scheduled_repo_distributor'
        schedule_id = 'scheduled_repo_publish'
        self.repo_manager.create_repo(repo_id)
        self.distributor_manager.add_distributor(repo_id, distributor_type_id, {}, False, distributor_id=distributor_id)

        # pre-condition
        self.assertEqual(len(self.distributor_manager.list_publish_schedules(repo_id, distributor_id)), 0)

        # add the schedule
        self.distributor_manager.add_publish_schedule(repo_id, distributor_id, schedule_id)
        self.assertTrue(schedule_id in self.distributor_manager.list_publish_schedules(repo_id, distributor_id))
        self.assertEqual(len(self.distributor_manager.list_publish_schedules(repo_id, distributor_id)), 1)

        # idempotent add
        self.distributor_manager.add_publish_schedule(repo_id, distributor_id, schedule_id)
        self.assertEqual(len(self.distributor_manager.list_publish_schedules(repo_id, distributor_id)), 1)

        # remove the schedule
        self.distributor_manager.remove_publish_schedule(repo_id, distributor_id, schedule_id)
        self.assertFalse(schedule_id in self.distributor_manager.list_publish_schedules(repo_id, distributor_id))
        self.assertEqual(len(self.distributor_manager.list_publish_schedules(repo_id, distributor_id)), 0)

        # idempotent remove
        self.distributor_manager.remove_publish_schedule(repo_id, distributor_id, schedule_id)
        self.assertEqual(len(self.distributor_manager.list_publish_schedules(repo_id, distributor_id)), 0)

        # errors
        self.distributor_manager.remove_distributor(repo_id, distributor_id)
        self.assertRaises(exceptions.MissingResource,
                          self.distributor_manager.add_publish_schedule,
                          repo_id, distributor_id, schedule_id)
        self.assertRaises(exceptions.MissingResource,
                          self.distributor_manager.remove_publish_schedule,
                          repo_id, distributor_id, schedule_id)


