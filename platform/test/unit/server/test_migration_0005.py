# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from base import PulpServerTests

from pulp.server.db import connection
from pulp.server.db.migrate.models import MigrationModule
from pulp.plugins.types.database import TYPE_COLLECTION_PREFIX

ID = '_id'
LAST_UPDATED = '_last_updated'
MIGRATION = 'pulp.server.db.migrations.0005_unit_last_updated'


def test_collections(n=3):
    names = []
    for suffix in range(0, n):
        name = TYPE_COLLECTION_PREFIX + str(suffix)
        names.append(name)
    return names


def test_units(n=10):
    units = []
    for unit_id in range(0, n):
        unit = {ID: unit_id}
        if unit_id % 2 == 0:
            unit[LAST_UPDATED] = 1
        units.append(unit)
    return units


TEST_COLLECTIONS = test_collections()
TEST_UNITS = test_units()


class TestMigration_0005(PulpServerTests):

    def setUp(self):
        self.clean()
        super(TestMigration_0005, self).setUp()
        for collection in [connection.get_collection(n, True) for n in TEST_COLLECTIONS]:
            for unit in TEST_UNITS:
                collection.save(unit, safe=True)

    def tearDown(self):
        super(TestMigration_0005, self).tearDown()
        self.clean()

    def clean(self):
        database = connection.get_database()
        for name in [n for n in database.collection_names() if n in TEST_COLLECTIONS]:
            database.drop_collection(name)

    def test(self):
        # migrate
        module = MigrationModule(MIGRATION)._module
        module.migrate()
        # validation
        for collection in [connection.get_collection(n) for n in TEST_COLLECTIONS]:
            for unit in collection.find({}):
                self.assertTrue(LAST_UPDATED in unit)
                unit_id = unit[ID]
                last_updated = unit[LAST_UPDATED]
                if unit_id % 2 == 0:
                    self.assertEqual(last_updated, 1)
                else:
                    self.assertTrue(isinstance(last_updated, float))
