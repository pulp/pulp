#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
from pulp.plugins.types import database, model
from pulp.server.db.connection import PulpCollection
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers.content.cud import ContentManager
from pulp.server.managers.content.query import ContentQueryManager

# constants --------------------------------------------------------------------

TYPE_1_DEF = model.TypeDefinition('type-1', 'Type 1', 'Test Definition One',
                                  ['key-1'], ['search-1'], [])

TYPE_2_DEF = model.TypeDefinition('type-2', 'Type 2', 'Test Definition Two',
                                  ['key-2a', 'key-2b'], [], ['type-1'])

TYPE_1_UNITS = [
    {'key-1': 'A',
     'search-1': 'one'},
    {'key-1': 'B',
     'search-1': 'one'},
    {'key-1': 'C',
     'search-1': 'two'}]

TYPE_2_UNITS = [
    {'key-2a': 'A',
     'key-2b': 'A'},
    {'key-2a': 'A',
     'key-2b': 'B'},
    {'key-2a': 'B',
     'key-2b': 'A'},
    {'key-2a': 'A',
     'key-2b': 'C'},
    {'key-2a': 'B',
     'key-2b': 'C'}]

# content manager base tests class ---------------------------------------------

class PulpContentTests(base.PulpServerTests):

    def setUp(self):
        super(PulpContentTests, self).setUp()
        database.update_database([TYPE_1_DEF, TYPE_2_DEF])
        self.cud_manager = ContentManager()
        self.query_manager = ContentQueryManager()

    def clean(self):
        super(PulpContentTests, self).clean()
        database.clean()

# cud unit tests ---------------------------------------------------------------

class PulpContentCUDTests(PulpContentTests):

    def test_add_content_unit(self):
        unit_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, TYPE_1_UNITS[0])
        self.assertNotEqual(unit_id, None)
        units = self.query_manager.list_content_units(TYPE_1_DEF.id)
        self.assertEqual(len(units), 1)

    def test_update_content_unit(self):
        unit_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, TYPE_1_UNITS[0])
        unit = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, unit_id)
        self.assertTrue(unit['search-1'] == 'one')
        self.cud_manager.update_content_unit(TYPE_1_DEF.id, unit_id, {'search-1': 'two'})
        unit = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, unit_id)
        self.assertTrue(unit['search-1'] == 'two')

    def test_delete_content_unit(self):
        unit_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, TYPE_1_UNITS[0])
        units = self.query_manager.list_content_units(TYPE_1_DEF.id)
        self.assertEqual(len(units), 1)
        self.cud_manager.remove_content_unit(TYPE_1_DEF.id, unit_id)
        units = self.query_manager.list_content_units(TYPE_1_DEF.id)
        self.assertEqual(len(units), 0)

    def test_link_child_unit(self):
        parent_id = self.cud_manager.add_content_unit(TYPE_2_DEF.id, None, TYPE_2_UNITS[0])
        child_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, TYPE_1_UNITS[0])
        self.cud_manager.link_referenced_content_units(TYPE_2_DEF.id, parent_id, TYPE_1_DEF.id, [child_id])
        parent = self.query_manager.get_content_unit_by_id(TYPE_2_DEF.id, parent_id)
        self.assertEqual(parent['_%s_references' % TYPE_1_DEF.id][0], child_id)

    def test_unlink_child_unit(self):
        parent_id = self.cud_manager.add_content_unit(TYPE_2_DEF.id, None, TYPE_2_UNITS[0])
        child_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, TYPE_1_UNITS[0])
        self.cud_manager.link_referenced_content_units(TYPE_2_DEF.id, parent_id, TYPE_1_DEF.id, [child_id])
        parent = self.query_manager.get_content_unit_by_id(TYPE_2_DEF.id, parent_id)
        self.assertEqual(len(parent['_%s_references' % TYPE_1_DEF.id]), 1)
        self.cud_manager.unlink_referenced_content_units(TYPE_2_DEF.id, parent_id, TYPE_1_DEF.id, [child_id])
        parent = self.query_manager.get_content_unit_by_id(TYPE_2_DEF.id, parent_id)
        self.assertEqual(len(parent['_%s_references' % TYPE_1_DEF.id]), 0)

# query unit tests -------------------------------------------------------------

class PulpContentQueryTests(PulpContentTests):

    def setUp(self):
        super(PulpContentQueryTests, self).setUp()
        self.type_1_ids = []
        self.type_2_ids = []
        for unit in TYPE_1_UNITS:
            unit_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, unit)
            self.type_1_ids.append(unit_id)
        for unit in TYPE_2_UNITS:
            unit_id = self.cud_manager.add_content_unit(TYPE_2_DEF.id, None, unit)
            self.type_2_ids.append(unit_id)

    def test_get_content_unit_collection(self):
        manager = ContentQueryManager()
        collection = manager.get_content_unit_collection('deb')
        self.assertTrue(isinstance(collection, PulpCollection))
        self.assertEqual(collection.name, 'units_deb')

    @mock.patch.object(ContentQueryManager, 'get_content_unit_collection')
    def test_find_by_criteria(self, mock_get_collection):
        criteria = Criteria(limit=20)
        units = self.query_manager.find_by_criteria('deb', criteria)

        # make sure it tried to get the correct collection
        mock_get_collection.assert_called_once_with('deb')

        # make sure the query call itself was correct
        mock_query = mock_get_collection.return_value.query
        self.assertEqual(mock_query.call_count, 1)
        self.assertEqual(mock_query.call_args[0][0], criteria)
        self.assertEqual(mock_query.return_value, units)

    def test_list(self):
        units = self.query_manager.list_content_units(TYPE_1_DEF.id)
        self.assertEqual(len(TYPE_1_UNITS), len(units))
        units = self.query_manager.list_content_units(TYPE_2_DEF.id)
        self.assertEqual(len(TYPE_2_UNITS), len(units))

    def test_get_by_id(self):
        unit = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, self.type_1_ids[0])
        self.assertEqual(unit['key-1'], TYPE_1_UNITS[0]['key-1'])

    def test_get_by_ids(self):
        units = self.query_manager.get_multiple_units_by_ids(TYPE_2_DEF.id, self.type_2_ids)
        self.assertEqual(len(units), len(self.type_2_ids))

    def test_key_dict(self):
        unit_ids, unit_keys = self.query_manager.get_content_unit_keys(TYPE_2_DEF.id, [self.type_2_ids[0]])
        self.assertEqual(len(unit_keys), 1)
        unit_id = unit_ids[0]
        unit_dict = unit_keys[0]
        unit_model = TYPE_2_UNITS[0]
        self.assertEqual(unit_id, self.type_2_ids[0])
        self.assertEqual(unit_dict['key-2a'], unit_model['key-2a'])
        self.assertEqual(unit_dict['key-2b'], unit_model['key-2b'])

    def test_get_by_key_dict(self):
        key_dict = self.query_manager.get_content_unit_keys(TYPE_2_DEF.id, [self.type_2_ids[0]])[1][0]
        unit = self.query_manager.get_content_unit_by_keys_dict(TYPE_2_DEF.id, key_dict)
        self.assertEqual(unit['_id'], self.type_2_ids[0])

    def test_multi_key_dicts(self):
        ids, key_dicts = self.query_manager.get_content_unit_keys(TYPE_2_DEF.id, self.type_2_ids)
        units = self.query_manager.get_multiple_units_by_keys_dicts(TYPE_2_DEF.id, key_dicts)
        self.assertEqual(len(units), len(self.type_2_ids))

    def __test_keys_dicts_query(self):
        # XXX this test proves my multi-dict query wrong, need to fix it
        new_unit = {'key-2a': 'B', 'key-2b': 'B'}
        unit_id = self.cud_manager.add_content_unit(TYPE_2_DEF.id, None, new_unit)
        keys_dicts = TYPE_2_UNITS[1:3]
        units = self.query_manager.get_multiple_units_by_keys_dicts(TYPE_2_DEF.id, keys_dicts)
        self.assertEqual(len(units), 2)
