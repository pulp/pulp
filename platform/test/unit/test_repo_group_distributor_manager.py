# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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

from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import RepositoryGroup
from pulp.server.db.model.repo_group import RepoGroup, RepoGroupDistributor
from pulp.server.exceptions import InvalidValue, MissingResource, PulpExecutionException, PulpDataException
from pulp.server.managers import factory as manager_factory

# -- test cases ---------------------------------------------------------------

class RepoGroupDistributorManagerTests(base.PulpServerTests):
    def setUp(self):
        super(RepoGroupDistributorManagerTests, self).setUp()
        mock_plugins.install()

        self.group_manager = manager_factory.repo_group_manager()
        self.distributor_manager = manager_factory.repo_group_distributor_manager()

        self.group_id = 'test-group'
        self.group_manager.create_repo_group(self.group_id)

    def tearDown(self):
        super(RepoGroupDistributorManagerTests, self).tearDown()
        mock_plugins.reset()

    def clean(self):
        super(RepoGroupDistributorManagerTests, self).clean()

        RepoGroup.get_collection().remove()
        RepoGroupDistributor.get_collection().remove()

    # -- add ------------------------------------------------------------------

    def test_add_distributor(self):
        # Setup
        config = {'a' : 'a', 'b' : None}

        # Test
        added = self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', config)

        # Verify
        expected_config = {'a' : 'a'}

        #   Returned Value
        self.assertTrue(added is not None)
        self.assertEqual(added['config'], expected_config)
        self.assertEqual(added['distributor_type_id'], 'mock-group-distributor')

        #   Database
        distributor = RepoGroupDistributor.get_collection().find_one({'id' : added['id']})
        self.assertTrue(distributor is not None)
        self.assertEqual(distributor['config'], expected_config)
        self.assertEqual(distributor['distributor_type_id'], 'mock-group-distributor')

        #   Plugin - Validate Config
        self.assertEqual(1, mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.call_count)
        call_group = mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.call_args[0][1]

        self.assertTrue(isinstance(call_group, RepositoryGroup))
        self.assertEqual(call_group.id, self.group_id)

        self.assertTrue(isinstance(call_config, PluginCallConfiguration))
        self.assertTrue(call_config.repo_plugin_config, expected_config)

        #   Plugin - Distributor Added
        self.assertEqual(1, mock_plugins.MOCK_GROUP_DISTRIBUTOR.distributor_added.call_count)
        call_group = mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.call_args[0][0]
        call_config = mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.call_args[0][1]

        self.assertTrue(isinstance(call_group, RepositoryGroup))
        self.assertTrue(isinstance(call_config, PluginCallConfiguration))

    def test_add_distributor_multiple_distributors(self):
        # Setup
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {})

        # Test
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {})

        # Verify
        all_distributors = list(RepoGroupDistributor.get_collection().find())
        self.assertEqual(2, len(all_distributors))

    def test_add_distributor_replace_existing(self):
        # Setup
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id='d1')

        # Test
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor-2', {}, distributor_id='d1')

        # Verify
        all_distributors = list(RepoGroupDistributor.get_collection().find())
        self.assertEqual(1, len(all_distributors))

        self.assertEqual(all_distributors[0]['distributor_type_id'], 'mock-group-distributor-2')

        # Plugin Calls
        self.assertEqual(1, mock_plugins.MOCK_GROUP_DISTRIBUTOR.distributor_added.call_count)
        self.assertEqual(1, mock_plugins.MOCK_GROUP_DISTRIBUTOR_2.distributor_added.call_count)
        self.assertEqual(1, mock_plugins.MOCK_GROUP_DISTRIBUTOR.distributor_removed.call_count)

    def test_add_distributor_invalid_id(self):
        bad_id = '!@#$%^&*()'
        try:
            self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id=bad_id)
            self.fail()
        except InvalidValue, e:
            self.assertTrue('distributor_id' in e.property_names)

    def test_add_distributor_no_group(self):
        try:
            self.distributor_manager.add_distributor('foo', 'mock-group-distributor', {})
            self.fail()
        except MissingResource, e:
            self.assertEqual(e.resources['repo_group'], 'foo')

    def test_add_distributor_no_distributor(self):
        try:
            self.distributor_manager.add_distributor(self.group_id, 'foo', {})
            self.fail()
        except InvalidValue, e:
            self.assertTrue('distributor_type_id' in e.property_names)

    def test_add_distributor_initialize_raises_error(self):
        # Setup
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.distributor_added.side_effect = Exception()

        # Test
        try:
            self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {})
            self.fail()
        except PulpExecutionException:
            pass

        # Cleanup
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.distributor_added.side_effect = None

    def test_add_distributor_validate_raises_error(self):
        # Setup
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.side_effect = Exception()

        # Test
        try:
            self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {})
            self.fail()
        except PulpDataException:
            pass

        # Cleanup
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.side_effect = None

    def test_add_distributor_invalid_config(self):
        # Setup
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.return_value = False, 'foo'

        # Test
        try:
            self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {})
            self.fail()
        except PulpDataException, e:
            self.assertEqual(e.args[0][0], 'foo')

    def test_add_distributor_with_related(self):
        # Setup
        self.group_manager.create_repo_group('group-a')
        self.group_manager.create_repo_group('group-b')

        self.distributor_manager.add_distributor('group-a', 'mock-group-distributor', {'1':1}, distributor_id='a1')
        self.distributor_manager.add_distributor('group-a', 'mock-group-distributor', {'2':2}, distributor_id='a2')
        self.distributor_manager.add_distributor('group-b', 'mock-group-distributor-2', {})

        # Test
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {})

        # Verify
        validate_args = mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.call_args[0]
        related_groups = validate_args[2]

        self.assertEqual(1, len(related_groups))
        self.assertEqual(related_groups[0].id, 'group-a')
        self.assertEqual(2, len(related_groups[0].plugin_configs))
        self.assertTrue({'1':1} in related_groups[0].plugin_configs)
        self.assertTrue({'2':2} in related_groups[0].plugin_configs)

    # -- remove ---------------------------------------------------------------

    def test_remove_distributor(self):
        # Setup
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id='d1')

        # Test
        self.distributor_manager.remove_distributor(self.group_id, 'd1')

        # Verify
        distributor = RepoGroupDistributor.get_collection().find_one({'id' : 'd1'})
        self.assertTrue(distributor is None)

    def test_remove_distributor_no_distributor(self):
        try:
            self.distributor_manager.remove_distributor(self.group_id, 'foo')
            self.fail()
        except MissingResource, e:
            self.assertEqual(e.resources['distributor'], 'foo')
            self.assertEqual(e.resources['repo_group'], self.group_id)

    def test_remove_distributor_no_group(self):
        try:
            self.distributor_manager.remove_distributor('bar', 'foo')
            self.fail()
        except MissingResource, e:
            self.assertEqual(e.resources['repo_group'], 'bar')
            self.assertTrue('distributor' not in e.resources)

    def test_remove_distributor_plugin_exception(self):
        # Setup
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.distributor_removed.side_effect = Exception()
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id='d1')

        # Test
        try:
            self.distributor_manager.remove_distributor(self.group_id, 'd1')
            self.fail()
        except PulpExecutionException, e:
            pass

    # -- update ---------------------------------------------------------------

    def test_update_distributor_config(self):
        # Setup
        orig = {'a' : 'a', 'b' : 'b', 'c' : 'c'}
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', orig, distributor_id='d1')

        # Test
        delta = {'a' : 'A', 'b' : None, 'd' : 'D'}
        self.distributor_manager.update_distributor_config(self.group_id, 'd1', delta)

        # Verify
        expected_config = {'a' : 'A', 'c' : 'c', 'd' : 'D'}

        #   Database
        distributor = self.distributor_manager.get_distributor(self.group_id, 'd1')
        self.assertEqual(expected_config, distributor['config'])

        #   Plugin Call
        self.assertEqual(2, mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.call_count)
        call_config = mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.call_args[0][1]
        self.assertEqual(expected_config, call_config.repo_plugin_config)

    def test_update_missing_group(self):
        try:
            self.distributor_manager.update_distributor_config('foo', 'bar', {})
            self.fail()
        except MissingResource, e:
            self.assertEqual(e.resources['repo_group'], 'foo')
            self.assertTrue('distributor' not in e.resources)

    def test_update_missing_distributor(self):
        try:
            self.distributor_manager.update_distributor_config(self.group_id, 'foo', {})
            self.fail()
        except MissingResource, e:
            self.assertEqual(e.resources['repo_group'], self.group_id)
            self.assertEqual(e.resources['distributor'], 'foo')

    def test_update_validate_exception(self):
        # Setup
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id='d1')
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.side_effect = Exception('foo')

        # Test
        try:
            self.distributor_manager.update_distributor_config(self.group_id, 'd1', {})
            self.fail()
        except PulpDataException, e:
            self.assertEqual(e.args[0][0], 'foo')

        # Cleanup
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.side_effect = None

    def test_update_invalid_config(self):
        # Setup
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id='d1')
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.validate_config.return_value = False, 'foo'

        # Test
        try:
            self.distributor_manager.update_distributor_config(self.group_id, 'd1', {})
            self.fail()
        except PulpDataException, e:
            self.assertEqual(e.args[0][0], 'foo')

    # -- scratchpad -----------------------------------------------------------

    def test_get_set_scratchpad(self):
        # Setup
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id='d1')

        # Test - Get Without Set
        sp = self.distributor_manager.get_distributor_scratchpad(self.group_id, 'd1')
        self.assertTrue(sp is None)

        # Test - Set
        value = {'a' : 'a'}
        self.distributor_manager.set_distributor_scratchpad(self.group_id, 'd1', value)

        # Test - Get
        sp = self.distributor_manager.get_distributor_scratchpad(self.group_id, 'd1')
        self.assertEqual(value, sp)

    # -- find -----------------------------------------------------------------

    def test_find_distributors(self):
        # Setup
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id='d1')
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id='d2')

        # Test
        matching = self.distributor_manager.find_distributors(self.group_id)

        # Verify
        self.assertEqual(2, len(matching))

    def test_find_distributors_no_group(self):
        # Test
        try:
            self.distributor_manager.find_distributors('foo')
            self.fail()
        except MissingResource, e:
            self.assertEqual(e.resources['repo_group'], 'foo')