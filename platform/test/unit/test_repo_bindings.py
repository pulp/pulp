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

from pulp.bindings.repository import RepositorySearchAPI, RepositoryUnitAPI

class TestRepoSearchAPI(unittest.TestCase):
    def test_path_defined(self):
        api = RepositorySearchAPI(mock.MagicMock())
        self.assertTrue(api.PATH is not None)
        self.assertTrue(len(api.PATH) > 0)


class TestRepoUnitSearchAPI(unittest.TestCase):
    def setUp(self):
        self.api = RepositoryUnitAPI(mock.MagicMock())

    @property
    def query(self):
        return self.api.server.POST.call_args[0][1]['criteria']

    def test_path(self):
        self.api.search('repo1', type_ids=['rpm'])
        path = self.api.server.POST.call_args[0][0]
        self.assertEqual(path, 'v2/repositories/repo1/search/units/')

    def test_sort(self):
        self.api.search('repo1', type_ids=['rpm'], sort=['id'])
        self.assertEqual(self.query['sort'], {'association': ['id']})

    def test_fields(self):
        self.api.search('repo1', type_ids=['rpm'], fields=['name'])
        self.assertEqual(self.query['fields'], {'unit': ['name']})

    def test_limit(self):
        self.api.search('repo1', type_ids=['rpm'], limit=20)
        self.assertEqual(self.query['limit'], 20)

    def test_skip(self):
        self.api.search('repo1', type_ids=['rpm'], skip=20)
        self.assertEqual(self.query['skip'], 20)

    def test_unit_filters(self):
        self.api.search('repo1', type_ids=['rpm'], lte=[('count', 5)])
        self.assertEqual(self.query['filters'],
                {'unit': {'count': {'$lte': 5}}})

    def test_after(self):
        self.api.search('repo1', type_ids=['rpm'], after='2012-03-15')
        self.assertEqual(self.query['filters']['association'],
                {'created': {'$gte': '2012-03-15'}})

    def test_before(self):
        self.api.search('repo1', type_ids=['rpm'], before='2012-03-15')
        self.assertEqual(self.query['filters']['association'],
                {'created': {'$lte': '2012-03-15'}})

class TestRepoUnitCopyAPI(unittest.TestCase):
    def setUp(self):
        self.api = RepositoryUnitAPI(mock.MagicMock())

    @property
    def query(self):
        return self.api.server.POST.call_args[0][1]['criteria']

    def test_path(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'])
        path = self.api.server.POST.call_args[0][0]
        self.assertEqual(path, 'v2/repositories/repo2/actions/associate/')

    def test_after(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'], after='2012-03-15')
        self.assertEqual(self.query['filters']['association'],
                {'created': {'$gte': '2012-03-15'}})

    def test_before(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'], before='2012-03-15')
        self.assertEqual(self.query['filters']['association'],
                {'created': {'$lte': '2012-03-15'}})

    def test_unit_filters(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'], lte=[('count', 5)])
        self.assertEqual(self.query['filters'],
                {'unit': {'count': {'$lte': 5}}})

    def test_source_repo_id(self):
        self.api.copy('repo1', 'repo2', type_ids=['rpm'])
        self.assertEqual(self.api.server.POST.call_args[0][1].get('source_repo_id', None), 'repo1')

