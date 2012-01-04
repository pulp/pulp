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

# Python
import datetime
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.content.types import database, model
from pulp.server.db.model.gc_repository import RepoContentUnit
from pulp.server.managers.repo._exceptions import InvalidOwnerType
import pulp.server.managers.repo.unit_association as association_manager
from pulp.server.managers.repo.unit_association import OWNER_TYPE_USER, OWNER_TYPE_IMPORTER
import pulp.server.managers.content.cud as content_cud_manager

# constants --------------------------------------------------------------------

TYPE_1_DEF = model.TypeDefinition('type-1', 'Type 1', 'Test Definition One',
                                  ['key-1'], ['search-1'], [])

TYPE_2_DEF = model.TypeDefinition('type-2', 'Type 2', 'Test Definition Two',
                                  ['key-2a', 'key-2b'], [], ['type-1'])

# -- cud test cases -----------------------------------------------------------

class RepoUnitAssociationManagerTests(testutil.PulpTest):

    def clean(self):
        super(RepoUnitAssociationManagerTests, self).clean()
        database.clean()
        RepoContentUnit.get_collection().remove()


    def setUp(self):
        super(RepoUnitAssociationManagerTests, self).setUp()
        database.update_database([TYPE_1_DEF, TYPE_2_DEF])
        self.manager = association_manager.RepoUnitAssociationManager()
        self.content_manager = content_cud_manager.ContentManager()

    def test_associate_by_id(self):
        """
        Tests creating a new association by content unit ID.
        """

        # Test
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-2', OWNER_TYPE_USER, 'admin')

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(2, len(repo_units))

        unit_ids = [u['unit_id'] for u in repo_units]
        self.assertTrue('unit-1' in unit_ids)
        self.assertTrue('unit-2' in unit_ids)

    def test_associate_by_id_existing(self):
        """
        Tests attempting to create a new association where one already exists.
        """

        # Test
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin') # shouldn't error

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual('unit-1', repo_units[0]['unit_id'])

    def test_associate_by_id_other_owner(self):
        """
        Tests making a second association using a different owner.
        """

        # Test
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_IMPORTER, 'test-importer')

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(2, len(repo_units))
        self.assertEqual('unit-1', repo_units[0]['unit_id'])
        self.assertEqual('unit-1', repo_units[1]['unit_id'])

    def test_associate_invalid_owner_type(self):
        # Test
        self.assertRaises(InvalidOwnerType, self.manager.associate_unit_by_id, 'repo-1', 'type-1', 'unit-1', 'bad-owner', 'irrelevant')

    def test_associate_all(self):
        """
        Tests making multiple associations in a single call.
        """

        # Test
        ids = ['foo', 'bar', 'baz']
        self.manager.associate_all_by_ids('repo-1', 'type-1', ids, OWNER_TYPE_USER, 'admin')

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(len(ids), len(repo_units))
        for unit in repo_units:
            self.assertTrue(unit['unit_id'] in ids)

    def test_unassociate_by_id(self):
        """
        Tests removing an association that exists by its unit ID.
        """

        # Setup
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-2', OWNER_TYPE_USER, 'admin')

        # Test
        self.manager.unassociate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual('unit-2', repo_units[0]['unit_id'])

    def test_unassociate_by_id_no_association(self):
        """
        Tests unassociating a unit where no association exists.
        """

        # Test - Make sure this does not raise an error
        self.manager.unassociate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')

    def test_unassociate_by_id_other_owner(self):
        """
        Tests that removing the association owned by one party doesn't affect another owner's association.
        """

        # Setup
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_IMPORTER, 'test-importer')

        # Test
        self.manager.unassociate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual('unit-1', repo_units[0]['unit_id'])

    def test_unassociate_all(self):
        """
        Tests unassociating multiple units in a single call.
        """

        # Setup
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-2', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-3', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id('repo-1', 'type-2', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id('repo-1', 'type-2', 'unit-2', OWNER_TYPE_USER, 'admin')

        unit_coll = RepoContentUnit.get_collection()
        self.assertEqual(5, len(list(unit_coll.find({'repo_id' : 'repo-1'}))))

        # Test
        self.manager.unassociate_all_by_ids('repo-1', 'type-1', ['unit-1', 'unit-2'], OWNER_TYPE_USER, 'admin')

        # Verify
        self.assertEqual(3, len(list(unit_coll.find({'repo_id' : 'repo-1'}))))

        self.assertTrue(unit_coll.find_one({'repo_id' : 'repo-1', 'unit_type_id' : 'type-1', 'unit_id' : 'unit-3'}) is not None)
        self.assertTrue(unit_coll.find_one({'repo_id' : 'repo-1', 'unit_type_id' : 'type-2', 'unit_id' : 'unit-1'}) is not None)
        self.assertTrue(unit_coll.find_one({'repo_id' : 'repo-1', 'unit_type_id' : 'type-2', 'unit_id' : 'unit-2'}) is not None)
