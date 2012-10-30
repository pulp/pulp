# -*- coding: utf-8 -*-
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

from pymongo.objectid import ObjectId

from base_db_upgrade import BaseDbUpgradeTests
from pulp.server.upgrade.db import units


class InitializeContentTypesTests(BaseDbUpgradeTests):

    def test_initialize_content_types(self):
        # Test
        result = units._initialize_content_types(self.tmp_test_db.database)

        # Verify
        self.assertTrue(result)

        types_coll = self.tmp_test_db.database.content_types
        migrations_coll = self.tmp_test_db.database.migration_trackers

        # Verify the proper creation of these collections
        types_indexes = types_coll.index_information()
        self.assertTrue('id_-1' in types_indexes)
        self.assertEqual(types_indexes['id_-1']['unique'], True)

        migrations_indexes = migrations_coll.index_information()
        self.assertTrue('name_-1' in migrations_indexes)
        self.assertEqual(migrations_indexes['name_-1']['unique'], True)

        for type_def in units.TYPE_DEFS:
            unit_coll = getattr(self.tmp_test_db.database, units._units_collection_name(type_def['id']))
            indexes = unit_coll.index_information()
            indexes.pop('_id_') # remove the default one, the other is named weird and this is easier
            self.assertEqual(len(indexes), 1) # sanity check, should be the unit_key
            index = indexes[indexes.keys()[0]]

            self.assertEqual(index['unique'], True)

            sorted_index_tuples = sorted(index['key'], key=lambda x : x[0])
            sorted_unit_key_names = sorted(type_def['unit_key'])

            for ituple, key_name in zip(sorted_index_tuples, sorted_unit_key_names):
                self.assertEqual(ituple[0], key_name)
                self.assertEqual(ituple[1], 1)

        # Verify the data itself
        for type_def in units.TYPE_DEFS:
            found_type = types_coll.find_one({'id' : type_def['id']})
            self.assertTrue(found_type is not None)
            self.assertTrue(isinstance(found_type['_id'], ObjectId))
            self.assertEqual(found_type['id'], type_def['id'])
            self.assertEqual(found_type['display_name'], type_def['display_name'])
            self.assertEqual(found_type['description'], type_def['description'])
            self.assertEqual(found_type['unit_key'], type_def['unit_key'])
            self.assertEqual(found_type['search_indexes'], type_def['search_indexes'])
            self.assertEqual(found_type['referenced_types'], type_def['referenced_types'])

            found_tracker = migrations_coll.find_one({'name' : type_def['display_name']})
            self.assertTrue(found_tracker is not None)
            self.assertTrue(isinstance(found_tracker['_id'], ObjectId))
            self.assertEqual(found_tracker['name'], type_def['display_name'])
            self.assertEqual(found_tracker['version'], 0)

