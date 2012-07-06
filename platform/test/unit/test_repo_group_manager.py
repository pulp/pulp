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

import traceback
import unittest

from base import PulpServerTests

from pulp.server import exceptions as pulp_exceptions
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.repository import Repo, RepoGroup
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.repo import group


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


class RepoGroupTests(PulpServerTests):

    def setUp(self):
        super(RepoGroupTests, self).setUp()
        self.collection = RepoGroup.get_collection()
        self.manager = group.RepoGroupManager()

    def tearDown(self):
        super(RepoGroupTests, self).tearDown()
        self.manager = None
        Repo.get_collection().remove(safe=True)
        RepoGroup.get_collection().remove(safe=True)

    def _create_repo(self, repo_id):
        manager = managers_factory.repo_manager()
        return manager.create_repo(repo_id)


class RepoGroupCUDTests(RepoGroupTests):

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
        original_notes = {'key_1': 'blonde'}
        self.manager.create_repo_group(group_id, notes=original_notes)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['notes'] == original_notes)

        updated_notes = {'key_1': 'brunette', 'key_2': 'ginger'}
        self.manager.update_repo_group(group_id, notes=updated_notes)

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group['notes'] == original_notes)
        self.assertTrue(group['notes'] == updated_notes)

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
        group_id = 'delete_me'
        self.manager.create_repo_group(group_id)

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group is None)

        self.manager.delete_repo_group(group_id)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group is None)


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


