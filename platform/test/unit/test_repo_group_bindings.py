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

from pulp.bindings.repo_groups import RepoGroupAPI, RepoGroupSearchAPI, RepoGroupActionAPI

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
        ret = self.api.associate('rg1')
        self.api.server.POST.assert_called_once_with(
            'v2/repo_groups/rg1/actions/associate/', {'criteria':{}})
        self.assertEqual(ret, self.api.server.POST.return_value.response_body)

    def test_unassociate(self):
        ret = self.api.unassociate('rg1')
        self.api.server.POST.assert_called_once_with(
            'v2/repo_groups/rg1/actions/unassociate/', {'criteria':{}})
        self.assertEqual(ret, self.api.server.POST.return_value.response_body)

