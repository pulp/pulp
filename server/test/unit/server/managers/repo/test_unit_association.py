#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
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

from .... import base
from pulp.devel import mock_plugins
from pulp.plugins.conduits.unit_import import ImportUnitConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository, Unit
from pulp.plugins.types import database, model
from pulp.server.db.model.auth import User
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.db.model.repository import RepoContentUnit, Repo, RepoImporter
import pulp.server.exceptions as exceptions
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.importer as importer_manager
import pulp.server.managers.repo.unit_association as association_manager
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

        self.manager = association_manager.RepoUnitAssociationManager()
        self.repo_manager = repo_manager.RepoManager()
        self.importer_manager = importer_manager.RepoImporterManager()
        self.content_manager = content_cud_manager.ContentManager()

        # Set up a valid configured repo for the tests
        self.repo_id = 'associate-repo'
        self.repo_manager.create_repo(self.repo_id)
        self.importer_manager.set_importer(self.repo_id, 'mock-importer', {})

        # Create units that can be associated to a repo
        self.unit_type_id = 'mock-type'

        self.unit_id = 'test-unit-id'
        self.unit_key = {'key-1' : 'test-unit'}
        self.content_manager.add_content_unit(self.unit_type_id, self.unit_id, self.unit_key)

        self.unit_id_2 = 'test-unit-id-2'
        self.unit_key_2 = {'key-1' : 'test-unit-2'}
        self.content_manager.add_content_unit(self.unit_type_id, self.unit_id_2, self.unit_key_2)

    def test_associate_by_id(self):
        """
        Tests creating a new association by content unit ID.
        """

        # Test
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-2', OWNER_TYPE_USER, 'admin')

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : self.repo_id}))
        self.assertEqual(2, len(repo_units))

        unit_ids = [u['unit_id'] for u in repo_units]
        self.assertTrue('unit-1' in unit_ids)
        self.assertTrue('unit-2' in unit_ids)

    def test_associate_by_id_existing(self):
        """
        Tests attempting to create a new association where one already exists.
        """

        # Test
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin') # shouldn't error

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : self.repo_id}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual('unit-1', repo_units[0]['unit_id'])

    def test_associate_by_id_other_owner(self):
        """
        Tests making a second association using a different owner.
        """

        # Test
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_IMPORTER, 'test-importer')

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : self.repo_id}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual('unit-1', repo_units[0]['unit_id'])

    def test_associate_invalid_owner_type(self):
        # Test
        self.assertRaises(exceptions.InvalidValue, self.manager.associate_unit_by_id, self.repo_id, 'type-1', 'unit-1', 'bad-owner', 'irrelevant')

    def test_associate_all(self):
        """
        Tests making multiple associations in a single call.
        """

        # Test
        ids = ['foo', 'bar', 'baz']
        ret = self.manager.associate_all_by_ids(self.repo_id, 'type-1', ids, OWNER_TYPE_USER, 'admin')

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : self.repo_id}))
        self.assertEqual(len(ids), len(repo_units))
        # return value should be the number of units that were associated
        self.assertEqual(ret, len(repo_units))
        for unit in repo_units:
            self.assertTrue(unit['unit_id'] in ids)

    def test_unassociate_by_id(self):
        """
        Tests removing an association that exists by its unit ID.
        """

        # Setup
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id, OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id_2, OWNER_TYPE_USER, 'admin')

        # Test
        self.manager.unassociate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id, OWNER_TYPE_USER, 'admin')

        # Verify
        repo_units = list(RepoContentUnit.get_collection().find({'repo_id' : self.repo_id}))
        self.assertEqual(1, len(repo_units))
        self.assertEqual(self.unit_id_2, repo_units[0]['unit_id'])

    def test_unassociate_by_id_no_association(self):
        """
        Tests unassociating a unit where no association exists.
        """

        # Test - Make sure this does not raise an error
        self.manager.unassociate_unit_by_id(self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')

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

        fake_user = User('associate-user', '')
        manager_factory.principal_manager().set_principal(principal=fake_user)

        mock_plugins.MOCK_IMPORTER.import_units.return_value = [Unit('mock-type', {'k' : 'v'}, {}, '')]

        # Test
        results = self.manager.associate_from_repo(source_repo_id, dest_repo_id)
        associated = results['units_successful']

        # Verify
        self.assertEqual(1, len(associated))
        self.assertEqual(associated[0]['type_id'], 'mock-type')
        self.assertEqual(associated[0]['unit_key'], {'k' : 'v'})

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.import_units.call_count)

        args = mock_plugins.MOCK_IMPORTER.import_units.call_args[0]
        kwargs = mock_plugins.MOCK_IMPORTER.import_units.call_args[1]
        self.assertTrue(isinstance(args[0], Repository)) # repository transfer object
        self.assertEqual(args[0].id, 'source-repo') # repo importing units from
        self.assertEqual(args[1].id, 'dest-repo') # repo importing units into
        self.assertEqual(None, kwargs['units']) # units to import
        self.assertTrue(isinstance(args[3], PluginCallConfiguration)) # config

        conduit = args[2]
        self.assertTrue(isinstance(conduit, ImportUnitConduit))
        self.assertEqual(conduit.association_owner_type, OWNER_TYPE_USER)
        self.assertEqual(conduit.association_owner_id, fake_user.login)

        # Clean Up
        manager_factory.principal_manager().set_principal(principal=None)

    def test_associate_from_repo_with_criteria(self):
        # Setup
        source_repo_id = 'source-repo'
        dest_repo_id = 'dest-repo'

        self.repo_manager.create_repo(source_repo_id)
        self.importer_manager.set_importer(source_repo_id, 'mock-importer', {})

        self.repo_manager.create_repo(dest_repo_id)
        self.importer_manager.set_importer(dest_repo_id, 'mock-importer', {})

        self.content_manager.add_content_unit('mock-type', 'unit-1', {'key-1' : 'unit-1', 'key-2':'foo', 'key-3':'bar'})
        self.content_manager.add_content_unit('mock-type', 'unit-2', {'key-1' : 'unit-2', 'key-2':'foo', 'key-3':'bar'})
        self.content_manager.add_content_unit('mock-type', 'unit-3', {'key-1' : 'unit-3', 'key-2':'foo', 'key-3':'bar'})

        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-2', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(source_repo_id, 'mock-type', 'unit-3', OWNER_TYPE_USER, 'admin')

        mock_plugins.MOCK_IMPORTER.import_units.return_value = [Unit('mock-type', {'k' : 'v'}, {}, '')]

        # Test
        overrides = { 'abc': '123'}
        criteria = UnitAssociationCriteria(type_ids=['mock-type'],
                                           unit_filters={'key-1' : 'unit-2'},
                                           unit_fields=['key-1', 'key-2'])
        results = self.manager.associate_from_repo(source_repo_id, dest_repo_id, criteria=criteria,
                                                      import_config_override=overrides)
        associated = results['units_successful']

        # Verify
        self.assertEqual(1, len(associated))
        self.assertEqual(associated[0]['type_id'], 'mock-type')
        self.assertEqual(associated[0]['unit_key'], {'k' : 'v'})

        self.assertEqual(1, mock_plugins.MOCK_IMPORTER.import_units.call_count)

        args = mock_plugins.MOCK_IMPORTER.import_units.call_args[0]
        kwargs = mock_plugins.MOCK_IMPORTER.import_units.call_args[1]
        for k,v in overrides.items():
            self.assertEqual(args[3].get(k), v)
        # make sure the criteria's "unit_fields" are being respected by giving
        # us key-2, but not key-3
        self.assertTrue('key-2' in kwargs['units'][0].metadata)
        self.assertTrue('key-3' not in kwargs['units'][0].metadata)
        self.assertEqual(1, len(kwargs['units']))
        self.assertEqual(kwargs['units'][0].id, 'unit-2')

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
        self.assertRaises(exceptions.MissingResource,
                          self.manager.associate_from_repo, source_repo_id, dest_repo_id)

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
        criteria = UnitAssociationCriteria(type_ids=['mock-type'], unit_filters={'key-1' : 'no way this matches squat'})
        ret = self.manager.associate_from_repo(source_repo_id, dest_repo_id, criteria=criteria)

        # Verify
        self.assertEqual(0, mock_plugins.MOCK_IMPORTER.import_units.call_count)
        self.assertEqual(ret.get('units_successful'), [])

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

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.update_unit_count')
    def test_associate_by_id_calls_update_unit_count(self, mock_call):
        self.manager.associate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')

        mock_call.assert_called_once_with(self.repo_id, 'type-1', 1)

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.update_last_unit_added')
    def test_associate_by_id_calls_update_last_unit_added(self, mock_call):
        self.manager.associate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')

        mock_call.assert_called_once_with(self.repo_id)

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.update_unit_count')
    def test_associate_by_id_does_not_call_update_unit_count(self, mock_call):
        """
        This would be the case when doing a bulk update.
        """
        self.manager.associate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin', False)
        self.assertFalse(mock_call.called)

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.update_unit_count')
    def test_associate_non_unique_by_id(self, mock_call):
        """
        non-unique call should not increment the count
        """
        self.manager.associate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')

        # creates a non-unique association for which the count should not be
        # incremented
        self.manager.associate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin2')
        self.assertEqual(mock_call.call_count, 1) # only from first associate

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.update_unit_count')
    def test_associate_all_by_ids_calls_update_unit_count(self, mock_call):
        IDS = ('foo', 'bar', 'baz')

        self.manager.associate_all_by_ids(
            self.repo_id, 'type-1', IDS, OWNER_TYPE_USER, 'admin')

        mock_call.assert_called_once_with(self.repo_id, 'type-1', len(IDS))

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.update_last_unit_added')
    def test_associate_all_by_id_calls_update_last_unit_added(self, mock_call):
        self.manager.associate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')

        mock_call.assert_called_once_with(self.repo_id)

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.update_unit_count')
    def test_associate_all_non_unique(self, mock_call):
        """
        Makes sure when two identical associations are requested, they only
        get counted once.
        """
        IDS = ('foo', 'bar', 'foo')

        self.manager.associate_all_by_ids(
            self.repo_id, 'type-1', IDS, OWNER_TYPE_USER, 'admin')

        mock_call.assert_called_once_with(self.repo_id, 'type-1', 2)

    def test_unassociate_all(self):
        """
        Tests unassociating multiple units in a single call.
        """

        # Setup
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id, OWNER_TYPE_USER, 'admin')
        # Add a different user to ensure they will remove properly
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id_2, OWNER_TYPE_IMPORTER, 'foo')
        self.manager.associate_unit_by_id(self.repo_id, 'type-2', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(self.repo_id, 'type-2', 'unit-2', OWNER_TYPE_USER, 'admin')

        unit_coll = RepoContentUnit.get_collection()
        self.assertEqual(4, len(list(unit_coll.find({'repo_id' : self.repo_id}))))

        # Test
        results = self.manager.unassociate_all_by_ids(self.repo_id, self.unit_type_id,
                                                           [self.unit_id, self.unit_id_2],
                                                           OWNER_TYPE_USER, 'admin')
        unassociated = results['units_successful']

        # Verify
        self.assertEqual(len(unassociated), 2)
        for u in unassociated:
            self.assertTrue(isinstance(u, dict))
            self.assertTrue(u['type_id'], self.unit_type_id)
            self.assertTrue(u['unit_key'] in [self.unit_key, self.unit_key_2])

        self.assertEqual(2, len(list(unit_coll.find({'repo_id' : self.repo_id}))))

        self.assertTrue(unit_coll.find_one({'repo_id' : self.repo_id, 'unit_type_id' : 'type-2', 'unit_id' : 'unit-1'}) is not None)
        self.assertTrue(unit_coll.find_one({'repo_id' : self.repo_id, 'unit_type_id' : 'type-2', 'unit_id' : 'unit-2'}) is not None)

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.update_unit_count')
    def test_unassociate_by_id_calls_update_unit_count(self, mock_call):
        self.manager.associate_unit_by_id(
            self.repo_id, self.unit_type_id, self.unit_id, OWNER_TYPE_USER, 'admin')
        self.manager.unassociate_unit_by_id(
            self.repo_id, self.unit_type_id, self.unit_id, OWNER_TYPE_USER, 'admin')

        self.assertEqual(2, mock_call.call_count)
        self.assertEqual(mock_call.call_args_list[0][0][0], self.repo_id)
        self.assertEqual(mock_call.call_args_list[1][0][1], self.unit_type_id)
        self.assertEqual(mock_call.call_args_list[0][0][2], 1)

        self.assertEqual(mock_call.call_args_list[1][0][0], self.repo_id)
        self.assertEqual(mock_call.call_args_list[1][0][1], self.unit_type_id)
        self.assertEqual(mock_call.call_args_list[1][0][2], -1)

    @mock.patch('pulp.server.managers.repo.cud.RepoManager.update_unit_count')
    def test_unassociate_by_id_non_unique(self, mock_call):
        self.manager.associate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin1')
        self.manager.associate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin2')

        # removes an association, but leaves a similar one behind, so the count
        # should not change
        self.manager.unassociate_unit_by_id(
            self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin1')
        self.assertEqual(mock_call.call_count, 1) # only once for the associates

    @mock.patch('pymongo.cursor.Cursor.count', return_value=1)
    def test_association_exists_true(self, mock_count):
        self.assertTrue(self.manager.association_exists(self.repo_id, 'unit-1', 'type-1'))
        self.assertEqual(mock_count.call_count, 1)

    @mock.patch('pymongo.cursor.Cursor.count', return_value=0)
    def test_association_exists_false(self, mock_count):
        self.assertFalse(self.manager.association_exists(self.repo_id, 'type-1', 'unit-1'))
        self.assertEqual(mock_count.call_count, 1)

    # unassociation via criteria tests -----------------------------------------

#        criteria_doc = {'association_filters': None,
#                        'unit_filters': None,
#                        'association_sort': None,
#                        'unit_sort': None,
#                        'limit': None,
#                        'skip': None,
#                        'association_fields': None,
#                        'unit_fields': None,
#                        'remove_duplicates': True}


    @mock.patch('pulp.server.managers.repo.cud.RepoManager.update_last_unit_removed')
    def test_unassociate_via_criteria(self, mock_call):
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id, OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(self.repo_id, self.unit_type_id, self.unit_id_2, OWNER_TYPE_USER, 'admin')

        criteria_doc = {'filters': {'association': {'unit_id': {'$in': [self.unit_id, 'unit-X']}}}}

        criteria = UnitAssociationCriteria.from_client_input(criteria_doc)

        self.manager.unassociate_by_criteria(self.repo_id, criteria, OWNER_TYPE_USER, 'admin')

        self.assertFalse(self.manager.association_exists(self.repo_id, self.unit_id, self.unit_type_id))
        self.assertTrue(self.manager.association_exists(self.repo_id, self.unit_id_2, self.unit_type_id))
        mock_call.assert_called_once_with(self.repo_id)

    def test_unassociate_via_criteria_no_matches(self):
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-1', OWNER_TYPE_USER, 'admin')
        self.manager.associate_unit_by_id(self.repo_id, 'type-1', 'unit-2', OWNER_TYPE_USER, 'admin')

        criteria_doc = {'type_ids': ['type-2']}

        criteria = UnitAssociationCriteria.from_client_input(criteria_doc)

        result = self.manager.unassociate_by_criteria(self.repo_id, criteria,
                                                      OWNER_TYPE_USER, 'admin')
        self.assertEquals(result, {})

        self.assertTrue(self.manager.association_exists(self.repo_id, 'unit-1', 'type-1'))
        self.assertTrue(self.manager.association_exists(self.repo_id, 'unit-2', 'type-1'))
