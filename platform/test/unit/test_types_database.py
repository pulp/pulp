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

import pulp.server.content.types.database as types_db
from pulp.server.content.types.model import TypeDefinition
from pulp.server.db.model.gc_content import ContentType
import pulp.server.db.connection as pulp_db

# -- constants -----------------------------------------------------------------

DEF_1 = TypeDefinition('def_1', 'Definition 1', 'Test definition',
                       'single_1', ['search_1'], [])
DEF_2 = TypeDefinition('def_2', 'Definition 2', 'Test definition',
                       ['single_1'], ['search_1'], [])
DEF_3 = TypeDefinition('def_3', 'Definition 3', 'Test definition',
                       ['compound_1', 'compound_2'], ['search_1'], [])
DEF_4 = TypeDefinition('def_4', 'Definition 4', 'Test definition',
                       'single_1', ['search_1'], [])

# -- test cases ----------------------------------------------------------------

class TypesDatabaseTests(testutil.PulpTest):

    def clean(self):
        super(TypesDatabaseTests, self).clean()
        types_db.clean()

    # -- public api tests ------------------------------------------------------

    def test_update_clean_database(self):
        """
        Tests calling update on a completely clean types database.
        """

        # Test
        defs = [DEF_1, DEF_2, DEF_3, DEF_4]
        types_db.update_database(defs)

        # Verify
        all_collection_names = types_db.all_type_collection_names()
        self.assertEqual(len(defs), len(all_collection_names))

        for d in defs:
            self.assertTrue(types_db.unit_collection_name(d.id) in all_collection_names)

            # Quick sanity check on the indexes
            collection = types_db.type_units_collection(d.id)
            all_indexes = collection.index_information()

            total_index_count = 1 + 1 + len(d.search_indexes) # _id + unit key + all search
            self.assertEqual(total_index_count, len(all_indexes))

    def test_update_no_changes(self):
        """
        Tests the common use case of loading type definitions that have been
        loaded already and have not changed.
        """

        # Setup
        defs = [DEF_1, DEF_2, DEF_3, DEF_4]
        types_db.update_database(defs)

        # Test
        same_defs = [DEF_4, DEF_3, DEF_2, DEF_1] # no real reason for this, just felt better than using the previous list
        types_db.update_database(same_defs)

        # Verify
        all_collection_names = types_db.all_type_collection_names()
        self.assertEqual(len(same_defs), len(all_collection_names))

        for d in defs:
            self.assertTrue(types_db.unit_collection_name(d.id) in all_collection_names)

            # Quick sanity check on the indexes
            collection = types_db.type_units_collection(d.id)
            all_indexes = collection.index_information()

            total_index_count = 1 + 1 + len(d.search_indexes) # _id + unit key + all search
            self.assertEqual(total_index_count, len(all_indexes))

    def test_update_missing_no_error(self):
        """
        Tests that updating a previously loaded database with some missing
        definitions does not throw an error.
        """

        # Setup
        defs = [DEF_1, DEF_2, DEF_3]
        types_db.update_database(defs)

        # Test
        new_defs = [DEF_4]
        types_db.update_database(new_defs)

        # Verify
        all_collection_names = types_db.all_type_collection_names()
        self.assertEqual(len(defs) + len(new_defs), len(all_collection_names)) # old are not deleted

        for d in defs:
            self.assertTrue(types_db.unit_collection_name(d.id) in all_collection_names)

            # Quick sanity check on the indexes
            collection = types_db.type_units_collection(d.id)
            all_indexes = collection.index_information()

            total_index_count = 1 + 1 + len(d.search_indexes) # _id + unit key + all search
            self.assertEqual(total_index_count, len(all_indexes))

    def test_update_missing_with_error(self):
        """
        Tests that updating a previously loaded database with some missing
        definitions correctly throws an error when requested.
        """

        # Setup
        defs = [DEF_1, DEF_2, DEF_3]
        types_db.update_database(defs)

        # Test
        new_defs = [DEF_4]

        try:
            types_db.update_database(new_defs, error_on_missing_definitions=True)
            self.fail('MissingDefinitions exception expected')
        except types_db.MissingDefinitions, e:
            self.assertEqual(3, len(e.missing_type_ids))
            self.assertTrue(DEF_1.id in e.missing_type_ids)
            self.assertTrue(DEF_2.id in e.missing_type_ids)
            self.assertTrue(DEF_3.id in e.missing_type_ids)
            print(e) # used to test the __str__ impl

    def test_update_failed_create(self):
        """
        Simulates a failure to create a collection by passing in a bad ID for
        the definition. 
        """

        # Setup
        busted = TypeDefinition('!@#$%^&*()', 'Busted', 'Busted', None, None, [])
        defs = [DEF_1, busted]

        # Tests
        try:
            types_db.update_database(defs)
            self.fail('Update with a failed create did not raise exception')
        except types_db.UpdateFailed, e:
            self.assertEqual(1, len(e.type_definitions))
            self.assertEqual(busted, e.type_definitions[0])
            print(e)

    def test_all_type_collection_names(self):
        """
        Tests listing all type collections.
        """

        # Setup
        type_def = TypeDefinition('rpm', 'RPM', 'RPM Packages', ['name'], ['name'], [])
        types_db._create_or_update_type(type_def)

        # Test
        all_names = types_db.all_type_collection_names()

        # Verify
        self.assertEqual(1, len(all_names))
        self.assertEqual(types_db.unit_collection_name(type_def.id), all_names[0])

    def test_all_type_collection_names_no_entries(self):
        """
        Tests listing all type collections when there are none in the database.
        """

        # Test
        names = types_db.all_type_collection_names()

        # Verify
        self.assertTrue(names is not None)
        self.assertEqual(0, len(names))

    def test_all_type_ids(self):
        """
        Tests listing all type IDs.
        """

        # Setup
        types_db._create_or_update_type(TypeDefinition('a', 'A', 'A', [], [], []))
        types_db._create_or_update_type(TypeDefinition('b', 'B', 'B', [], [], []))

        # Test
        type_ids = types_db.all_type_ids()

        # Verify
        self.assertEqual(2, len(type_ids))
        self.assertTrue('a' in type_ids)
        self.assertTrue('b' in type_ids)

    def test_all_type_ids_no_entries(self):
        """
        Tests that an empty list (not None) is returned when there are no types.
        """

        # Test
        type_ids = types_db.all_type_ids()

        # Verify
        self.assertTrue(type_ids is not None)
        self.assertTrue(isinstance(type_ids, list))
        self.assertEqual(0, len(type_ids))

    def test_all_type_definitions(self):
        """
        Tests retrieving all type definitions from the database.
        """

        # Setup
        defs = [DEF_1, DEF_2, DEF_3, DEF_4]
        types_db.update_database(defs)

        # Test
        all_defs = types_db.all_type_definitions()

        # Verify
        self.assertEqual(4, len(all_defs))

    def test_type_units_unit_key(self):
        """
        Tests the syntactic sugar method for retrieving unit key on a type.
        """

        # Setup
        type_def = TypeDefinition('rpm', 'RPM', 'RPM Packages', ['unique_1', 'unique_2'], ['name'], [])
        types_db._create_or_update_type(type_def)

        # Test
        unit_key = types_db.type_units_unit_key('rpm')

        # Verify
        self.assertEqual(type_def.unit_key, unit_key)

    def test_type_units_unique_indexes_missing_def(self):
        """
        Tests no error is raised when requesting the indexes on a type that does not exist.
        """

        # Test
        indexes = types_db.type_units_unit_key('not_there')

        # Verify
        self.assertTrue(indexes is None)

    # -- utility method tests ------------------------------------------------

    def test_create_or_update_type_collection(self):
        """
        Tests the call to create a new type collection works.
        """

        # Setup
        type_def = TypeDefinition('rpm', 'RPM', 'RPM Packages', ['name'], ['name'], [])

        # Test
        types_db._create_or_update_type(type_def)

        # Verify

        #   Present in types collection
        all_types = list(ContentType.get_collection().find())
        self.assertEqual(1, len(all_types))

        found = all_types[0]
        self.assertEqual(type_def.id, found['id'])
        self.assertEqual(type_def.display_name, found['display_name'])
        self.assertEqual(type_def.description, found['description'])
        self.assertEqual(type_def.unit_key, found['unit_key'])
        self.assertEqual(type_def.search_indexes, found['search_indexes'])

        #   Type collection exists
        collection_name = types_db.unit_collection_name(type_def.id)
        self.assertTrue(collection_name in pulp_db.database().collection_names())

    def test_create_or_update_existing_type_collection(self):
        """
        Tests calling create_or_update with a change to an existing type
        collection is successful.
        """

        # Setup
        type_def = TypeDefinition('rpm', 'RPM', 'RPM Packages', ['name'], ['name'], [])
        types_db._create_or_update_type(type_def)

        # Test
        type_def.display_name = 'new-name'
        type_def.description = 'new-description'
        type_def.unit_key = 'new-key'
        type_def.search_indexes = None
        types_db._create_or_update_type(type_def)

        # Verify

        #   Present in types collection
        all_types = list(ContentType.get_collection().find())
        self.assertEqual(1, len(all_types))

        found = all_types[0]
        self.assertEqual(type_def.id, found['id'])
        self.assertEqual(type_def.display_name, found['display_name'])
        self.assertEqual(type_def.description, found['description'])
        self.assertEqual(type_def.unit_key, found['unit_key'])
        self.assertEqual(type_def.search_indexes, found['search_indexes'])

        #   Type collection exists
        collection_name = types_db.unit_collection_name(type_def.id)
        self.assertTrue(collection_name in pulp_db.database().collection_names())

    def test_update_unit_key_single_field(self):
        """
        Tests a single field unit key is handled correctly.
        """

        # Setup
        unit_key = 'individual_1',
        type_def = TypeDefinition('rpm', 'RPM', 'RPM Packages', unit_key, None, [])

        # Test
        types_db._update_unit_key(type_def)

        # Verify
        collection_name = types_db.unit_collection_name(type_def.id)
        collection = pulp_db.get_collection(collection_name)

        index_dict = collection.index_information()

        self.assertEqual(2, len(index_dict)) # default (_id) + unit key

        index = index_dict['individual_1_1']
        self.assertTrue(index['unique'])

        keys = index['key']
        self.assertEqual(1, len(keys))
        self.assertEqual('individual_1', keys[0][0])
        self.assertEqual(types_db.ASCENDING, keys[0][1])

    def test_update_unit_key_multiple_fields(self):
        """
        Tests that a multiple field unit key is built as a single, compound index
        """

        # Setup
        unit_key = ['compound_1', 'compound_2']
        type_def = TypeDefinition('rpm', 'RPM', 'RPM Packages', unit_key, None, [])

        # Test
        types_db._update_unit_key(type_def)

        # Verify
        collection_name = types_db.unit_collection_name(type_def.id)
        collection = pulp_db.get_collection(collection_name)

        index_dict = collection.index_information()

        self.assertEqual(2, len(index_dict)) # default (_id) + unit key

        index = index_dict['compound_1_1_compound_2_1']
        self.assertTrue(index['unique'])

        keys = index['key']
        self.assertEqual(2, len(keys))
        self.assertEqual('compound_1', keys[0][0])
        self.assertEqual(types_db.ASCENDING, keys[0][1])
        self.assertEqual('compound_2', keys[1][0])
        self.assertEqual(types_db.ASCENDING, keys[1][1])

    def test_update_search_indexes(self):
        """
        Tests that the unique index creation on a new collection is successful.
        This will test both single key and compound indexes to ensure mongo
        handles them successfully.
        """

        # Setup
        search_indexes = [
            ['compound_1', 'compound_2'],
            'individual_1'
        ]
        type_def = TypeDefinition('rpm', 'RPM', 'RPM Packages', None, search_indexes, [])

        # Test
        types_db._update_search_indexes(type_def)

        # Verify
        collection_name = types_db.unit_collection_name(type_def.id)
        collection = pulp_db.get_collection(collection_name)

        index_dict = collection.index_information()

        self.assertEqual(3, len(index_dict)) # default (_id) + definition ones

        #   Verify individual index
        index = index_dict['individual_1_1']

        keys = index['key']
        self.assertEqual(1, len(keys))
        self.assertEqual('individual_1', keys[0][0])
        self.assertEqual(types_db.ASCENDING, keys[0][1])

        #   Verify compound index
        index = index_dict['compound_1_1_compound_2_1']

        keys = index['key']
        self.assertEqual(2, len(keys))
        self.assertEqual('compound_1', keys[0][0])
        self.assertEqual(types_db.ASCENDING, keys[0][1])
        self.assertEqual('compound_2', keys[1][0])
        self.assertEqual(types_db.ASCENDING, keys[1][1])

    def test_drop_indexes(self):
        """
        Tests updating indexes on an existing collection with different indexes correctly changes them.
        """

        # Setup
        old_key = ['compound_1', 'compound_2']

        type_def = TypeDefinition('rpm', 'RPM', 'RPM Packages', old_key, None, [])
        types_db._update_unit_key(type_def)

        # Test
        new_key = ['new_1']
        type_def.unit_key = new_key

        types_db._drop_indexes(type_def)
        types_db._update_unit_key(type_def)

        # Verify
        collection_name = types_db.unit_collection_name(type_def.id)
        collection = pulp_db.get_collection(collection_name)

        index_dict = collection.index_information()

        self.assertEqual(2, len(index_dict)) # default (_id) + new one
