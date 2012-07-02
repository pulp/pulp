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
import mock

from pulp.plugins.conduits.unit_import import ImportUnitConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository, Unit
from pulp.plugins.types import database, model
from pulp.server.db.model.repository import RepoContentUnit, Repo, RepoImporter
import pulp.server.exceptions as exceptions
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.importer as importer_manager
import pulp.server.managers.repo.unit_association as association_manager
from pulp.server.managers.repo.unit_association_query import Criteria
from pulp.server.managers.repo.unit_association import OWNER_TYPE_USER, OWNER_TYPE_IMPORTER
import pulp.server.managers.content.cud as content_cud_manager
import pulp.server.managers.factory as manager_factory

# constants --------------------------------------------------------------------

TYPE_1_DEF = model.TypeDefinition('type-1', 'Type 1', 'Test Definition One',
                                  ['key-1'], ['search-1'], [])

TYPE_2_DEF = model.TypeDefinition('type-2', 'Type 2', 'Test Definition Two',
                                  ['key-2a', 'key-2b'], [], ['type-1'])

MOCK_TYPE_DEF = model.TypeDefinition('mock-type', 'Mock Type', 'Used by the mock importer',
                                     ['key-1'], [], [])

# -- cud test cases -----------------------------------------------------------

class RepoUnitAssociationManagerTests(base.PulpServerTests):

    def clean(self):
        super(RepoUnitAssociationManagerTests, self).clean()
        database.clean()
        RepoContentUnit.get_collection().remove()
        RepoImporter.get_collection().remove()
        Repo.get_collection().remove()

    def tearDown(self):
        super(RepoUnitAssociationManagerTests, self).tearDown()
        mock_plugins.reset()
        manager_factory.reset()

    def setUp(self):
        super(RepoUnitAssociationManagerTests, self).setUp()
        database.update_database([TYPE_1_DEF, TYPE_2_DEF, MOCK_TYPE_DEF])
        mock_plugins.install()
        # so we don't try to refresh the unit count on non-existing repos
        manager_factory._CLASSES[manager_factory.TYPE_REPO] = mock.MagicMock()

        self.manager = association_manager.RepoUnitAssociationManager()
        self.repo_manager = repo_manager.RepoManager()
        self.importer_manager = importer_manager.RepoImporterManager()
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
        self.assertRaises(exceptions.InvalidValue, self.manager.associate_unit_by_id, 'repo-1', 'type-1', 'unit-1', 'bad-owner', 'irrelevant')

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

    def test_associate_from_repo_no_criteria(self):
        # Setup
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.repo_manager.create_repo(source_repo_id)
        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})

        self.repo_manager.create_repo(dest_repo_id)
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        self.content_manager.add_content_unit('mock-type', 'unit-1', {'key-1' : 'unit-1'})
        self.content_manager.add_content_unit('mock-type', 'unit-2', {'key-1' : 'unit-2'})
        self.content_manager.add_content_unit('mock-type', 'unit-3', {'key-1' : 'unit-3'})

        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-2', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-3', OWNER_TYPE_USER, 'admin')

        # Test
        self.manager.associate_from_repo(source_repo_id, dest_repo_id)

        # Verify
        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.import_units.call_count)

        args = mock_plugins.MOCK_IMPORTER.import_units.call_args[0]
        kwargs = mock_plugins.MOCK_IMPORTER.import_units.call_args[1]
        self.assertTrue(isinstance(args[0], Repository)) # repository transfer object
        self.assertEqual(args[0].id, 'source-repo') # repo importing units from
        self.assertEqual(args[1].id, 'dest-repo') # repo importing units into
        self.assertEqual(None, kwargs['units']) # units to import
        self.assertTrue(isinstance(args[2], ImportUnitConduit)) # conduit
        self.assertTrue(isinstance(args[3], PluginCallConfiguration)) # config

    def test_associate_from_repo_with_criteria(self):
        # Setup
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.repo_manager.create_repo(source_repo_id)
        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})

        self.repo_manager.create_repo(dest_repo_id)
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        self.content_manager.add_content_unit('mock-type', 'unit-1', {'key-1' : 'unit-1'})
        self.content_manager.add_content_unit('mock-type', 'unit-2', {'key-1' : 'unit-2'})
        self.content_manager.add_content_unit('mock-type', 'unit-3', {'key-1' : 'unit-3'})

        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-2', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-3', OWNER_TYPE_USER, 'admin')

        # Test
        criteria = Criteria(type_ids=['mock-type'], unit_filters={'key-1' : 'unit-2'}, unit_fields=['key-1'])
        self.manager.associate_from_repo(source_repo_id, dest_repo_id, criteria=criteria)

        # Verify
        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.import_units.call_count)

        kwargs = mock_plugins.MOCK_IMPORTER.import_units.call_args[1]
        self.assertEqual(1, len(kwargs['units']))
        self.assertEqual(kwargs['units'][0].id, 'unit-2')

    def test_associate_from_repo_with_dependencies(self):
        # Setup
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.repo_manager.create_repo(source_repo_id)
        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})

        self.repo_manager.create_repo(dest_repo_id)
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        dep_transfer_units = [
            Unit('mock-type', {'key-1' : 'unit-x'}, {}, 'p1'),
        ]
        mock_plugins.MOCK_IMPORTER.resolve_dependencies.return_value = dep_transfer_units

        self.content_manager.add_content_unit('mock-type', 'unit-1', {'key-1' : 'unit-1'})
        self.content_manager.add_content_unit('mock-type', 'unit-2', {'key-1' : 'unit-2'})
        self.content_manager.add_content_unit('mock-type', 'unit-3', {'key-1' : 'unit-3'})
        self.content_manager.add_content_unit('mock-type', 'unit-x', {'key-1' : 'unit-x'})

        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-2', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-3', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-x', OWNER_TYPE_USER, 'admin')

        # Test
        criteria = Criteria(type_ids=['mock-type'], unit_filters={'key-1' : 'unit-2'}, unit_fields=['key-1'])
        self.manager.associate_from_repo(source_repo_id, dest_repo_id, criteria=criteria, with_dependencies=True)

        # Verify
        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.import_units.call_count)

        kwargs = mock_plugins.MOCK_IMPORTER.import_units.call_args[1]
        self.assertEqual(2, len(kwargs['units'])) # 1 matching criteria, 1 deps

        sorted_transfer_units = sorted(kwargs['units'], key=lambda x : x.unit_key['key-1'])
        self.assertEqual(sorted_transfer_units[0].unit_key['key-1'], 'unit-2')
        self.assertEqual(sorted_transfer_units[1].unit_key['key-1'], 'unit-x')

    def test_associate_from_repo_dest_has_no_importer(self):
        # Setup
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.repo_manager.create_repo(source_repo_id)
        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})

        self.repo_manager.create_repo(dest_repo_id)
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        self.manager.associate_unit_by_id(source_repo_id, 'bad-type', 'unit-1', OWNER_TYPE_USER, 'admin')

        # Test
        try:
            self.manager.associate_from_repo(source_repo_id, dest_repo_id)
            self.fail('Exception expected')
        except exceptions.InvalidValue, e:
            pass

    def test_associate_from_repo_dest_unsupported_types(self):
        # Setup
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.repo_manager.create_repo(source_repo_id)
        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})

        self.repo_manager.create_repo(dest_repo_id)

        # Test
        try:
            self.manager.associate_from_repo(source_repo_id, dest_repo_id)
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            print(e)

    def test_associate_from_repo_importer_error(self):
        # Setup
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.repo_manager.create_repo(source_repo_id)
        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})

        self.repo_manager.create_repo(dest_repo_id)
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.import_units.side_effect = Exception()

        self.content_manager.add_content_unit('mock-type', 'unit-1', {'key-1' : 'unit-1'})
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-1', OWNER_TYPE_USER, 'admin')

        # Test
        try:
            self.manager.associate_from_repo(source_repo_id, dest_repo_id)
            self.fail('Exception expected')
        except exceptions.PulpExecutionException:
            pass

        # Cleanup
        mock_plugins.MOCK_IMPORTER.import_units.side_effect = None

    def test_associate_from_repo_no_matching_units(self):
        # Setup
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.repo_manager.create_repo(source_repo_id)
        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})

        self.repo_manager.create_repo(dest_repo_id)
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        # Test
        criteria = Criteria(type_ids=['mock-type'], unit_filters={'key-1' : 'no way this matches squat'})
        self.manager.associate_from_repo(source_repo_id, dest_repo_id, criteria=criteria)

        # Verify
        self.assertEqual(0, mock_plugins.MOCK_IMPORTER.import_units.call_count)

    def test_associate_from_repo_missing_source(self):
        # Setup
        dest_repo_id = 'dest-repo'

        self.repo_manager.create_repo(dest_repo_id)
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        # Test
        try:
            self.manager.associate_from_repo('missing', dest_repo_id)
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('missing' == e.resources['repo_id'])

    def test_associate_from_repo_missing_destination(self):
        # Setup
        source_repo_id = 'source-repo'

        self.repo_manager.create_repo(source_repo_id)
        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})

        # Test
        try:
            self.manager.associate_from_repo(source_repo_id, 'missing')
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('missing' == e.resources['repo_id'])

    def test_associate_by_id_calls_update_unit_count(self):
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        mock_manager = manager_factory.repo_manager()
        mock_manager.update_unit_count.assert_called_once_with('repo-1', 1)

    def test_associate_by_id_does_not_call_update_unit_count(self):
        """
        This would be the case when doing a bulk update.
        """
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin', False)
        mock_manager = manager_factory.repo_manager()
        self.assertFalse(mock_manager.update_unit_count.called)

    def test_associate_non_unique_by_id(self):
        """
        non-unique call should not increment the count
        """
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        mock_manager = manager_factory.repo_manager()
        mock_manager.update_unit_count.reset_mock()

        # creates a non-unique association for which the count should not be
        # incremented
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin2')
        self.assertEqual(mock_manager.update_unit_count.called, False)

    def test_associate_all_by_ids_calls_update_unit_count(self):
        IDS = ('foo', 'bar', 'baz')

        self.manager.associate_all_by_ids(
            'repo-1', 'type-1', IDS, OWNER_TYPE_USER, 'admin')

        mock_manager = manager_factory.repo_manager()
        mock_manager.update_unit_count.assert_called_once_with(
            'repo-1', len(IDS))

    def test_associate_all_non_unique(self):
        """
        Makes sure when two identical associations are requested, they only
        get counted once.
        """
        IDS = ('foo', 'bar', 'foo')

        self.manager.associate_all_by_ids(
            'repo-1', 'type-1', IDS, OWNER_TYPE_USER, 'admin')

        mock_manager = manager_factory.repo_manager()
        mock_manager.update_unit_count.assert_called_once_with(
            'repo-1', 2)

    def test_unassociate_by_id_calls_update_unit_count(self):
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        mock_manager = manager_factory.repo_manager()
        mock_manager.reset_mock()
        self.manager.unassociate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        mock_manager.update_unit_count.assert_called_once_with('repo-1', -1)

    def test_unassociate_by_id_non_unique(self):
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin1')
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin2')
        mock_manager = manager_factory.repo_manager()
        mock_manager.reset_mock()

        # removes an association, but leaves a similar one behind, so the count
        # should not change
        self.manager.unassociate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin1')
        self.assertFalse(mock_manager.update_unit_count.called)

    def test_unassociate_by_id_does_not_call_update_unit_count(self):
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        mock_manager = manager_factory.repo_manager()
        mock_manager.reset_mock()
        self.manager.unassociate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin', False)
        self.assertFalse(mock_manager.update_unit_count.called)

    def test_unassociate_all_by_ids_calls_update_unit_count(self):
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-2', OWNER_TYPE_USER, 'admin')
        mock_manager = manager_factory.repo_manager()
        mock_manager.reset_mock()
        self.manager.unassociate_all_by_ids(
            'repo-1', 'type-1', ('unit-1', 'unit-2'), OWNER_TYPE_USER, 'admin')
        mock_manager.update_unit_count.assert_called_once_with('repo-1', -2)

    def test_unassociate_all_non_unique(self):
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin1')
        self.manager.associate_unit_by_id(
            'repo-1', 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin2')
        mock_manager = manager_factory.repo_manager()
        mock_manager.reset_mock()

        # removes an association, but leaves a similar one behind, so the count
        # should not change
        self.manager.unassociate_all_by_ids(
            'repo-1', 'type-1', ('unit-1',), OWNER_TYPE_USER, 'admin')
        self.assertFalse(mock_manager.update_unit_count.called)

    @mock.patch('pymongo.cursor.Cursor.count', return_value=1)
    def test_association_exists_true(self, mock_count):
        self.assertTrue(self.manager.association_exists('repo-1', 'unit-1', 'type-1'))
        self.assertEqual(mock_count.call_count, 1)

    @mock.patch('pymongo.cursor.Cursor.count', return_value=0)
    def test_association_exists_false(self, mock_count):
        self.assertFalse(self.manager.association_exists('repo-1', 'type-1', 'unit-1'))
        self.assertEqual(mock_count.call_count, 1)