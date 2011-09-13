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
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.db.model.gc_repository import RepoContentUnit
import pulp.server.managers.repo.unit_association as association_manager

# -- test cases ---------------------------------------------------------------

class RepoUnitAssociationManagerTests(testutil.PulpTest):

    def clean(self):
        super(RepoUnitAssociationManagerTests, self).clean()

        RepoContentUnit.get_collection().remove()

    def setUp(self):
        super(RepoUnitAssociationManagerTests, self).setUp()

        self.manager = association_manager.RepoUnitAssociationManager()

    def test_associate_by_id(self):
        """
        Tests creating a new association by content unit ID.
        """

        # Test
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1')
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-2')

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
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1')
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1') # shouldn't error

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual('unit-1', repo_units[0]['unit_id'])

    def test_associate_by_key(self):
        """
        Tests creating a new association by unit key.
        """
        pass

    def test_associate_by_key_existing(self):
        """
        Tests attempting to create a new association where one already exists.
        """
        pass

    def test_unassociate_by_id(self):
        """
        Tests removing an association that exists by its unit ID.
        """

        # Setup
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-1')
        self.manager.associate_unit_by_id('repo-1', 'type-1', 'unit-2')

        # Test
        self.manager.unassociate_unit_by_id('repo-1', 'type-1', 'unit-1')

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual('unit-2', repo_units[0]['unit_id'])

    def test_unassociate_by_id_no_association(self):
        """
        Tests unassociating a unit where no association exists.
        """

        # Test - Make sure this does not raise an error
        self.manager.unassociate_unit_by_id('repo-1', 'type-1', 'unit-1')
