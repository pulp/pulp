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
import json
import os
import unittest

from mock import mock_open, patch

from pulp.server.db import manage
from pulp.server.db.version import VERSION
import base
import pulp.plugins.types.database as types_db


# These are used for mocking
def _fake_listdir(*args, **kwargs):
    return ['test_type.json']


_test_type_json = '''{"types": [{
    "id" : "test_type_id",
    "display_name" : "Test Type",
    "description" : "Test Type",
    "unit_key" : ["attribute_1", "attribute_2", "attribute_3"],
    "search_indexes" : ["attribute_1", "attribute_3"]
}]}'''


def _fake_get_version_in_use(*args, **kwargs):
    return VERSION


class TestTypeImporting(base.PulpServerTests):
    def clean(self):
        super(self.__class__, self).clean()
        types_db.clean()

    @patch('__builtin__.open', mock_open(read_data=_test_type_json))
    @patch('os.listdir', _fake_listdir)
    @patch('sys.argv', ["pulp-manage-db", "--force"])
    @patch('pulp.server.db.manage.get_version_in_use', _fake_get_version_in_use)
    def test_pulp_manage_db_loads_types(self):
        """
        Test calling pulp-manage-db imports types on a clean types database.
        """
        manage.main()

        all_collection_names = types_db.all_type_collection_names()
        self.assertEqual(len(all_collection_names), 1)

        self.assertEqual(['units_test_type_id'], all_collection_names)

        # Let's make sure we loaded the type definitions correctly
        db_type_definitions = types_db.all_type_definitions()
        self.assertEquals(len(db_type_definitions), 1)
        test_json = json.loads(_test_type_json)
        for attribute in ['id', 'display_name', 'description', 'unit_key', 'search_indexes']:
            self.assertEquals(test_json['types'][0][attribute], db_type_definitions[0][attribute])

        # Now let's ensure that we 
        collection = types_db.type_units_collection('test_type_id')
        self.assertEqual(collection.index_information(), {
            u'_id_': {u'key': [(u'_id', 1)], u'v': 1},
            u'attribute_1_1_attribute_2_1_attribute_3_1': {u'unique': True, u'v': 1,
                                                           u'dropDups': False,
                                                           u'key': [(u'attribute_1', 1),
                                                                    (u'attribute_2', 1),
                                                                    (u'attribute_3', 1)]},
            u'attribute_1_1': {u'v': 1, u'dropDups': False, u'key': [(u'attribute_1', 1)]},
            u'attribute_3_1': {u'v': 1, u'dropDups': False, u'key': [(u'attribute_3', 1)]}})


class TestDatabaseMigrations(base.PulpServerTests):
    @unittest.expectedFailure
    def test_migrate_platform(self):
        self.fail()
