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

import unittest

import mock

from pulp.bindings.repo_groups import RepoGroupAPI, RepoGroupDistributorAPI, RepoGroupSearchAPI, \
    RepoGroupActionAPI
from pulp.common.plugins import distributor_constants


class TestRepoGroupAPI(unittest.TestCase):
    def setUp(self):
        self.api = RepoGroupAPI(mock.MagicMock())

    def test_path(self):
        self.assertTrue(isinstance(self.api.PATH, basestring))
        self.assertTrue(len(self.api.PATH) > 0)
        # this should be a relative path, and thus not start with a '/'
        self.assertFalse(self.api.PATH.startswith('/'))

    def test_repo_groups(self):
        ret = self.api.repo_groups()
        self.api.server.GET.assert_called_once_with(self.api.PATH)
        self.assertEqual(ret, self.api.server.GET.return_value)

    def test_create(self):
        REPOGROUP = {
            'id' : 'rg1',
            'display_name' : 'repo group 1',
            'description' : 'great group',
            'notes' : {'awesome' : True}
        }
        ret = self.api.create(**REPOGROUP)
        self.api.server.POST.assert_called_once_with(self.api.PATH, REPOGROUP)

    def test_create_and_configure(self):
        """
        Test that create_and_configure results in the correct call to POST and returns whatever POST
        returns
        """
        # Setup
        group_id, display_name, description = 'test_id', 'test group', 'test description'
        distributors = [{'fake': 'distributor'}]
        notes = {'key': True}
        expected_repo_group = {
            'id': group_id,
            'display_name': display_name,
            'description': description,
            'notes': notes,
            'distributors': distributors,
        }

        # Test
        result = self.api.create_and_configure(group_id, display_name, description, notes, distributors)
        self.api.server.POST.assert_called_once_with(self.api.PATH, expected_repo_group)
        self.assertEqual(result, self.api.server.POST.return_value)

    def test_repogroup(self):
        ret = self.api.repo_group('rg1')
        expected_path = self.api.PATH + 'rg1/'
        self.api.server.GET.assert_called_once_with(expected_path)
        self.assertEqual(ret, self.api.server.GET.return_value)

    def test_delete(self):
        ret = self.api.delete('rg1')
        expected_path = self.api.PATH + 'rg1/'
        self.api.server.DELETE.assert_called_once_with(expected_path)
        self.assertEqual(ret, self.api.server.DELETE.return_value)

    def test_update(self):
        DELTA = {'display_name':'foo'}
        ret = self.api.update('rg1', DELTA)
        expected_path = self.api.PATH + 'rg1/'
        self.api.server.PUT.assert_called_once_with(expected_path, DELTA)
        self.assertEqual(ret, self.api.server.PUT.return_value)


class TestRepoGroupDistributorAPI(unittest.TestCase):
    """
    A set of tests for the RepoGroupDistributorAPI
    """
    def setUp(self):
        self.api = RepoGroupDistributorAPI(mock.MagicMock())

    def test_distributors(self):
        """
        Test that the server is called with the expected path and that the
        RepoGroupDistributorAPI.distributors method passes the server return value back up.
        """
        result = self.api.distributors('group_id')
        expected_path = self.api.PATH % 'group_id'
        self.api.server.GET.assert_called_once_with(expected_path)
        self.assertEqual(result, self.api.server.GET.return_value)

    def test_create(self):
        """
        Test creating a distributor and associating it with a group
        """
        # Setup
        group_id = 'test_id'
        expected_path = self.api.PATH % group_id
        distributor_type = 'fake_type'
        distributor_config = {'fake': 'config'}
        expected_data = {distributor_constants.DISTRIBUTOR_TYPE_ID_KEY: distributor_type,
                         distributor_constants.DISTRIBUTOR_CONFIG_KEY: distributor_config,
                         distributor_constants.DISTRIBUTOR_ID_KEY: None}

        # Test
        result = self.api.create(group_id, distributor_type, distributor_config)
        self.api.server.POST.assert_called_once_with(expected_path, expected_data)
        self.assertEqual(result, self.api.server.POST.return_value)

    def test_distributor(self):
        """
        Test retrieving a distributor that is associated with a group
        """
        # Setup
        group_id, distributor_id = 'test_id', 'test_distributor_id'
        expected_path = self.api.PATH % group_id + distributor_id + '/'

        # Test
        result = self.api.distributor(group_id, distributor_id)
        self.api.server.GET.assert_called_once_with(expected_path)
        self.assertEqual(result, self.api.server.GET.return_value)

    def test_delete(self):
        """
        Test removing a distributor that is associated with a group
        """
        # Setup
        group_id, distributor_id = 'test_id', 'test_distributor_id'
        expected_path = self.api.PATH % group_id + distributor_id + '/'

        # Test
        result = self.api.delete(group_id, distributor_id)
        self.api.server.DELETE.assert_called_once_with(expected_path)
        self.assertEqual(result, self.api.server.DELETE.return_value)

    def test_update(self):
        """
        Test updating a distributor that is associated with a group
        """
        # Setup
        group_id, distributor_id = 'test_id', 'test_distributor_id'
        distributor_config = {'fake': 'config'}
        expected_path = self.api.PATH % group_id + distributor_id + '/'

        # Test
        result = self.api.update(group_id, distributor_id, distributor_config)
        self.api.server.PUT.assert_called_once_with(expected_path, distributor_config)
        self.assertEqual(result, self.api.server.PUT.return_value)


class TestRepoGroupSearchAPI(unittest.TestCase):
    def setUp(self):
        self.api = RepoGroupSearchAPI(mock.MagicMock())

    def test_path(self):
        self.assertTrue(isinstance(self.api.PATH, basestring))
        self.assertTrue(len(self.api.PATH) > 0)
        # this should be a relative path, and thus not start with a '/'
        self.assertFalse(self.api.PATH.startswith('/'))


class TestRepoGroupActionAPI(unittest.TestCase):
    def setUp(self):
        self.api = RepoGroupActionAPI(mock.MagicMock())

    def test_path(self):
        self.assertTrue(isinstance(self.api.PATH, basestring))
        self.assertTrue(len(self.api.PATH) > 0)
        # this should be a relative path, and thus not start with a '/'
        self.assertFalse(self.api.PATH.startswith('/'))

    def test_associate(self):
        ret = self.api.associate('rg1', match=[('name', 'foo')])
        EXPECTED = {'criteria': {'filters': {'name': {'$regex' : 'foo'}}}}
        self.api.server.POST.assert_called_once_with(
            'v2/repo_groups/rg1/actions/associate/', EXPECTED)
        self.assertEqual(ret, self.api.server.POST.return_value.response_body)

    def test_unassociate(self):
        ret = self.api.unassociate('rg1', match=[('name', 'foo')])
        EXPECTED = {'criteria': {'filters': {'name': {'$regex' : 'foo'}}}}
        self.api.server.POST.assert_called_once_with(
            'v2/repo_groups/rg1/actions/unassociate/', EXPECTED)
        self.assertEqual(ret, self.api.server.POST.return_value.response_body)

    def test_publish(self):
        """
        Test publishing a repository group results in the correct POST
        """
        result = self.api.publish('repo_group1', 'distributor_id', {'config': 'value'})
        expected_data = {'id': 'distributor_id', 'override_config': {'config': 'value'}}
        self.api.server.POST.assert_called_once_with(
            'v2/repo_groups/repo_group1/actions/publish/', expected_data)
        self.assertEqual(result, self.api.server.POST.return_value)
