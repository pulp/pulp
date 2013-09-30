# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import os
import shutil
import traceback
import unittest

import mock

from base import PulpAsyncServerTests
from pulp.devel import mock_plugins
from pulp.common.plugins import distributor_constants
from pulp.server import exceptions as pulp_exceptions
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.repo_group import RepoGroup, RepoGroupDistributor
from pulp.server.db.model.repository import Repo
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.repo import _common as common_utils
from pulp.server.managers.repo.group import cud


class RepoGroupManagerInstantiationTests(unittest.TestCase):

    def test_constructor(self):
        try:
            RepoGroup('contructor_group')
        except:
            self.fail(traceback.format_exc())

    def test_factory(self):
        try:
            managers_factory.repo_group_manager()
        except:
            self.fail(traceback.format_exc())


class RepoGroupTests(PulpAsyncServerTests):

    def setUp(self):
        super(RepoGroupTests, self).setUp()
        self.collection = RepoGroup.get_collection()
        self.manager = cud.RepoGroupManager()

    def tearDown(self):
        super(RepoGroupTests, self).tearDown()
        self.manager = None
        Repo.get_collection().remove(safe=True)
        RepoGroup.get_collection().remove(safe=True)
        RepoGroupDistributor.get_collection().remove(safe=True)

    def _create_repo(self, repo_id):
        manager = managers_factory.repo_manager()
        return manager.create_repo(repo_id)


class RepoGroupCUDTests(RepoGroupTests):

    def setUp(self):
        super(RepoGroupCUDTests, self).setUp()
        mock_plugins.install()

    def tearDown(self):
        super(RepoGroupCUDTests, self).tearDown()
        mock_plugins.reset()

    def test_create(self):
        group_id = 'create_group'
        self.manager.create_repo_group(group_id)
        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group is None)

    def test_create_duplicate_id(self):
        group_id = 'already_exists'
        self.manager.create_repo_group(group_id)
        self.assertRaises(pulp_exceptions.DuplicateResource,
                          self.manager.create_repo_group,
                          group_id)

    @mock.patch('pulp.server.managers.repo.group.cud.RepoGroupManager.create_repo_group',
                spec_set=cud.RepoGroupManager.create_repo_group, return_value='potato')
    def test_create_and_config_no_distributors(self, create_repo_group):
        """
        Tests creating a repo group using create_and_configure_repo_group using only the
        required arguments.
        """
        # Test that create_repo_group is called with the correct arguments
        result = self.manager.create_and_configure_repo_group('group_id1')
        self.assertEqual(1, self.manager.create_repo_group.call_count)
        self.assertEqual((('group_id1', None, None, None, None),),
                         self.manager.create_repo_group.call_args)
        self.assertEqual('potato', result)

    @mock.patch('pulp.server.managers.repo.group.cud.RepoGroupManager.create_repo_group',
                spec_set=cud.RepoGroupManager.create_repo_group, return_value='potato')
    @mock.patch(
        'pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager.add_distributor')
    def test_create_and_config_distributors(self, mock_add_distributor, create_repo_group):
        """
        Tests creating a repo group and adding distributors
        """
        group_id = 'group_id1'
        display_name = 'A display name'
        description = 'A test repo group'
        notes = {'key': 'value'}
        distributor_list = [{distributor_constants.DISTRIBUTOR_TYPE_ID_KEY: 'fake_distributor',
                             distributor_constants.DISTRIBUTOR_CONFIG_KEY: {'a': 1},
                             distributor_constants.DISTRIBUTOR_ID_KEY: 'fake_id'}]
        repo_ids = ['repo1', 'repo2']

        # Assert that create_repo_group was called with all the correct arguments
        result = self.manager.create_and_configure_repo_group(group_id, display_name, description,
                                                              repo_ids, notes, distributor_list)
        self.assertEqual(1, self.manager.create_repo_group.call_count)
        self.assertEqual(((group_id, display_name, description, repo_ids, notes),),
                         self.manager.create_repo_group.call_args)
        self.assertEqual('potato', result)

        # Assert add_distributor was called with all the correct arguments
        self.assertEqual(1, mock_add_distributor.call_count)
        self.assertEqual(group_id, mock_add_distributor.call_args[0][0])
        self.assertEqual('fake_distributor', mock_add_distributor.call_args[0][1])
        self.assertEqual({'a': 1}, mock_add_distributor.call_args[0][2])
        self.assertEqual('fake_id', mock_add_distributor.call_args[0][3])

    # Mock out delete because we expect it to be called when distributor validation fails
    @mock.patch('pulp.server.managers.repo.group.cud.RepoGroupManager.delete_repo_group',
                spec_set=cud.RepoGroupManager.delete_repo_group)
    @mock.patch('pulp.server.managers.repo.group.cud.RepoGroupManager.create_repo_group',
                spec_set=cud.RepoGroupManager.create_repo_group, return_value='potato')
    def test_create_and_config_bad_distributor_list(self, create_repo_group, delete_repo_group):
        """
        Test creating a repo group with a distributor_list that isn't a list, tuple or None
        """
        # Test that an exception is raised and a group is not created
        self.assertRaises(
            pulp_exceptions.InvalidValue,
            self.manager.create_and_configure_repo_group, group_id='id', distributor_list='string')
        self.assertEqual(0, self.manager.create_repo_group.call_count)

    @mock.patch('pulp.server.managers.repo.group.cud.RepoGroupManager.create_repo_group',
                spec_set=cud.RepoGroupManager.create_repo_group, return_value='potato')
    def test_create_and_config_bad_distributor(self, create_repo_group):
        """
        Test creating a repo group with a distributor that is not a dictionary
        """
        # Test that an exception is raised and a group is not created
        self.assertRaises(
            pulp_exceptions.InvalidValue, self.manager.create_and_configure_repo_group,
            group_id='id', distributor_list=['not a dict'])
        self.assertEqual(0, self.manager.create_repo_group.call_count)

    @mock.patch('pulp.server.managers.repo.group.cud.RepoGroupManager.delete_repo_group',
                spec_set=cud.RepoGroupManager.delete_repo_group)
    @mock.patch('pulp.server.managers.repo.group.cud.RepoGroupManager.create_repo_group',
                spec_set=cud.RepoGroupManager.create_repo_group, return_value='potato')
    @mock.patch(
        'pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager.add_distributor')
    def test_create_and_config_failed_dist_add(self, mock_add_distributor, create_repo_group,
                                               delete_repo_group):
        """
        Test creating a repo group which results the distributor manager raising an InvalidValue
        """
        mock_add_distributor.side_effect = pulp_exceptions.InvalidValue(['everything'])

        # Test that if add_distributor fails, an exception is raised and the created group is
        # cleaned up
        self.assertRaises(
            pulp_exceptions.InvalidValue, self.manager.create_and_configure_repo_group,
            group_id='id', distributor_list=[{}])
        self.manager.create_repo_group.assert_called_once_with('id', None, None, None, None)
        self.manager.delete_repo_group.assert_called_once_with('id')

    def test_update_display_name(self):
        group_id = 'update_me'
        original_display_name = 'Update Me'
        self.manager.create_repo_group(group_id, display_name=original_display_name)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['display_name'] == original_display_name)

        new_display_name = 'Updated!'
        self.manager.update_repo_group(group_id, display_name=new_display_name)

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group['display_name'] == original_display_name)
        self.assertTrue(group['display_name'] == new_display_name)

    def test_update_description(self):
        group_id = 'update_me'
        original_description = 'This is a repo group that needs to be updated :P'
        self.manager.create_repo_group(group_id, description=original_description)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['description'] == original_description)

        new_description = 'This repo group has been updated! :D'
        self.manager.update_repo_group(group_id, description=new_description)

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group['description'] == original_description)
        self.assertTrue(group['description'] == new_description)

    def test_update_notes(self):
        group_id = 'notes'
        original_notes = {'key_1': 'blonde', 'key_3': 'brown'}
        self.manager.create_repo_group(group_id, notes=original_notes)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['notes'] == original_notes)

        delta = {'key_2': 'ginger', 'key_3': ''}
        self.manager.update_repo_group(group_id, notes=delta)

        group = self.collection.find_one({'id': group_id})
        self.assertEqual(group['notes'].get('key_1', None), 'blonde')
        self.assertEqual(group['notes'].get('key_2', None), 'ginger')
        self.assertTrue('key_3' not in group['notes'])

    def test_set_note(self):
        group_id = 'noteworthy'
        self.manager.create_repo_group(group_id)

        key = 'package'
        value = ['package_dependencies']
        note = {key: value}
        self.manager.set_note(group_id, key, value)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['notes'] == note)

    def test_unset_note(self):
        group_id = 'not_noteworthy'
        notes = {'marital_status': 'polygamist'}
        self.manager.create_repo_group(group_id, notes=notes)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['notes'] == notes)

        self.manager.unset_note(group_id, 'marital_status')

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group['notes'])

    def test_delete(self):
        # Setup
        group_id = 'delete_me'
        self.manager.create_repo_group(group_id)

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group is None)

        # Simulate the working dir being created by a plugin
        working_dir = common_utils.repo_group_working_dir(group_id)
        if os.path.exists(working_dir):
            shutil.rmtree(working_dir)
        os.makedirs(working_dir)
        self.assertTrue(os.path.exists(working_dir))

        # Test
        self.manager.delete_repo_group(group_id)

        # Verify
        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group is None)

        # Ensure the working dir was deleted
        self.assertTrue(not os.path.exists(working_dir))

    def test_delete_with_distributor(self):
        # Setup
        group_id = 'doomed'
        self.manager.create_repo_group(group_id)

        distributor_id = 'doomed-dist'
        dist_manager = managers_factory.repo_group_distributor_manager()
        dist_manager.add_distributor(group_id, 'mock-group-distributor', {}, distributor_id=distributor_id)

        distributor = RepoGroupDistributor.get_collection().find_one({'id' : distributor_id})
        self.assertTrue(distributor is not None)

        # Test
        self.manager.delete_repo_group(group_id)

        # Verify
        distributor = RepoGroupDistributor.get_collection().find_one({'id' : distributor_id})
        self.assertTrue(distributor is None)

class RepoGroupMembershipTests(RepoGroupTests):

    def test_add_single(self):
        group_id = 'test_group'
        self.manager.create_repo_group(group_id)

        repo = self._create_repo('test_repo')
        criteria = Criteria(filters={'id': repo['id']}, fields=['id'])
        self.manager.associate(group_id, criteria)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(repo['id'] in group['repo_ids'])

    def test_remove_single(self):
        group_id = 'test_group'
        repo = self._create_repo('test_repo')
        self.manager.create_repo_group(group_id, repo_ids=[repo['id']])

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(repo['id'] in group['repo_ids'])

        criteria = Criteria(filters={'id': repo['id']}, fields=['id'])
        self.manager.unassociate(group_id, criteria)

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(repo['id'] in group['repo_ids'])

    def test_delete_repo(self):
        group_id = 'delete_from_me'
        repo = self._create_repo('delete_me')
        self.manager.create_repo_group(group_id, repo_ids=[repo['id']])

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(repo['id'] in group['repo_ids'])

        repo_manager = managers_factory.repo_manager()
        repo_manager.delete_repo(repo['id'])

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(repo['id'] in group['repo_ids'])

    def test_associate_id_regex(self):
        group_id = 'associate_by_regex'
        self.manager.create_repo_group(group_id)

        repo_1 = self._create_repo('repo_1')
        repo_2 = self._create_repo('repo_2')
        criteria = Criteria(filters={'id': {'$regex': 'repo_[12]'}})
        self.manager.associate(group_id, criteria)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(repo_1['id'] in group['repo_ids'])
        self.assertTrue(repo_2['id'] in group['repo_ids'])


