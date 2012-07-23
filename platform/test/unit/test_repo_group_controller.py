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

import mock

import base

from pulp.server.db.model.repository import Repo
from pulp.server.db.model.repo_group import RepoGroup
from pulp.server.managers import factory as manager_factory

class RepoGroupCollectionTests(base.PulpWebserviceTests):

    def setUp(self):
        super(RepoGroupCollectionTests, self).setUp()

        self.manager = manager_factory.repo_group_manager()

    def clean(self):
        super(RepoGroupCollectionTests, self).clean()

        Repo.get_collection().remove()
        RepoGroup.get_collection().remove()

    def test_get(self):
        # Setup
        self.manager.create_repo_group('group-1')
        self.manager.create_repo_group('group-2')

        # Test
        status, body = self.get('/v2/repo_groups/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(2, len(body))

        ids = [g['id'] for g in body]
        self.assertTrue('group-1' in ids)
        self.assertTrue('group-2' in ids)

    def test_get_no_groups(self):
        # Test
        status, body = self.get('/v2/repo_groups/')

        # Verify
        self.assertEqual(200, status)
        self.assertTrue(isinstance(body, list))
        self.assertEqual(0, len(body))

    def test_post(self):
        # Setup
        data = {
            'id' : 'post-group',
            'display_name' : 'Post Group',
            'description' : 'Post Description',
        }

        # Test
        status, body = self.post('/v2/repo_groups/', data)

        # Verify
        self.assertEqual(201, status)

        found = RepoGroup.get_collection().find_one({'id' : data['id']})
        self.assertTrue(found is not None)
        for k, v in data.items():
            self.assertEqual(found[k], v)

    def test_post_missing_value(self):
        # Test
        status, body = self.post('/v2/repo_groups/', {})

        # Verify
        self.assertEqual(400, status)

    def test_post_extra_keys(self):
        # Test
        status, body = self.post('/v2/repo_groups/', {'extra' : 'e'})

        # Verify
        self.assertEqual(400, status)

    def test_post_with_repos(self):
        # Setup
        manager_factory.repo_manager().create_repo('add-me')

        data = {
            'id' : 'with-repos',
            'repo_ids' : ['add-me']
        }

        # Test
        status, body = self.post('/v2/repo_groups/', data)

        # Verify
        self.assertEqual(201, status)

        found = RepoGroup.get_collection().find_one({'id' : data['id']})
        self.assertEqual(found['repo_ids'], data['repo_ids'])

class RepoGroupResourceTests(base.PulpWebserviceTests):

    def setUp(self):
        super(RepoGroupResourceTests, self).setUp()

        self.manager = manager_factory.repo_group_manager()

    def clean(self):
        super(RepoGroupResourceTests, self).clean()

        RepoGroup.get_collection().remove()

    def test_get(self):
        # Setup
        group_id = 'created'
        self.manager.create_repo_group(group_id)

        # Test
        status, body = self.get('/v2/repo_groups/%s/' % group_id)

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(body['id'], group_id)

    def test_get_missing_group(self):
        # Test
        status, body = self.get('/v2/repo_groups/missing/')

        # Verify
        self.assertEqual(404, status)

    def test_delete(self):
        # Setup
        group_id = 'doomed'
        self.manager.create_repo_group(group_id)

        # Test
        status, body = self.delete('/v2/repo_groups/%s/' % group_id)

        # Verify
        self.assertEqual(200, status)

        found = RepoGroup.get_collection().find_one({'id' : group_id})
        self.assertTrue(found is None)

    def test_delete_missing_group(self):
        # Test
        status, body = self.delete('/v2/repo_groups/missing/')

        # Verify
        self.assertEqual(404, status)

    def test_update(self):
        # Setup
        group_id = 'update-me'
        self.manager.create_repo_group(group_id, display_name='Original')

        # Test
        changed = {'display_name' : 'Updated'}
        status, body = self.put('/v2/repo_groups/%s/' % group_id, changed)

        # Verify
        self.assertEqual(200, status)

        found = RepoGroup.get_collection().find_one({'id' : group_id})
        self.assertEqual(changed['display_name'], found['display_name'])
