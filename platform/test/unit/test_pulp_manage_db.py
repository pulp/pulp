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
import os
import unittest

from mock import mock_open, patch

from pulp.common.compat import json
from pulp.server.db import manage
from pulp.server.db.migrate import utils
from pulp.server.db.model.migration_tracker import MigrationTracker
import base
import pulp.plugins.types.database as types_db
import test_migration_packages
import test_migration_packages.platform


# This is used for mocking
_test_type_json = '''{"types": [{
    "id" : "test_type_id",
    "display_name" : "Test Type",
    "description" : "Test Type",
    "unit_key" : ["attribute_1", "attribute_2", "attribute_3"],
    "search_indexes" : ["attribute_1", "attribute_3"]
}]}'''


class MigrationTest(base.PulpServerTests):
    def clean(self):
        base.PulpServerTests.clean(self)
        # Make sure each test doesn't have any lingering MigrationTrackers
        MigrationTracker.get_collection().remove({})


class TestManageDB(MigrationTest):
    def clean(self):
        super(self.__class__, self).clean()
        types_db.clean()

    @unittest.expectedFailure
    def test_migrate_platform(self):
        self.fail()

    @patch('__builtin__.open', mock_open(read_data=_test_type_json))
    @patch('os.listdir', return_value=['test_type.json'])
    @patch('sys.argv', ["pulp-manage-db",])
    def test_pulp_manage_db_loads_types(self, listdir_mock):
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

        # Now let's ensure that we have the correct indexes 
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


class TestMigrationPackage(MigrationTest):
    def test_migrations(self):
        migration_package = utils.MigrationPackage('test_migration_packages.z')
        migrations = migration_package.migrations
        self.assertEqual(len(migrations), 3)
        self.assertTrue(all([isinstance(migration, utils.MigrationModule)
                        for migration in migrations]))
        # Make sure their versions are set and sorted appropriately
        self.assertEqual([1, 2, 3], [migration.version for migration in migrations])
        # Check the names
        self.assertEqual(['test_migration_packages.z.0001_test',
                          'test_migration_packages.z.0002_test',
                          'test_migration_packages.z.0003_test'],
                         [migration._module.__name__ for migration in migrations])


class TestMigrationTracker(MigrationTest):
    def test___init__(self):
        mt = MigrationTracker('meaning_of_life', 42)
        self.assertEquals(mt.name, 'meaning_of_life')
        self.assertEquals(mt.version, 42)
        self.assertEquals(mt._collection, MigrationTracker.get_collection())

    def test_save(self):
        # Make sure we are starting off clean
        self.assertEquals(MigrationTracker.get_collection().find({}).count(), 0)
        # Instantiate a MigrationTracker
        mt = MigrationTracker('meaning_of_life', 41)
        # At this point there should not be a MigrationTracker in the database
        self.assertEquals(mt._collection.find({}).count(), 0)
        # saving the mt should add it to the DB
        mt.save()
        self.assertEquals(mt._collection.find({}).count(), 1)
        mt_bson = mt._collection.find_one({'name': 'meaning_of_life'})
        self.assertEquals(mt_bson['name'], 'meaning_of_life')
        self.assertEquals(mt_bson['version'], 41)
        # now let's update the version to 42, the correct meaning of life
        mt.version = 42
        mt.save()
        # see if the updated meaning of life made it to the DB
        self.assertEquals(mt._collection.find({}).count(), 1)
        mt_bson = mt._collection.find_one({'name': 'meaning_of_life'})
        self.assertEquals(mt_bson['name'], 'meaning_of_life')
        self.assertEquals(mt_bson['version'], 42)


class TestMigrationUtils(MigrationTest):
    @patch('pulp.server.db.migrate.utils.migrations', test_migration_packages)
    @patch('pulp.server.db.migrate.utils.pulp.server.db.migrations.platform',
           test_migration_packages.platform)
    def test_get_migration_packages(self):
        """
        Ensure that pulp.server.db.migrate.utils.get_migration_packages functions correctly.
        """
        packages = utils.get_migration_packages()
        self.assertEquals(len(packages), 3)
        self.assertTrue(all([isinstance(package, utils.MigrationPackage) for package in packages]))
        # Make sure that the packages are sorted correctly, with platform first
        self.assertEquals(packages[0].name, 'test_migration_packages.platform')
        self.assertEquals(packages[1].name, 'test_migration_packages.a')
        self.assertEquals(packages[2].name, 'test_migration_packages.z')

    def test__import_all_the_way(self):
        """
        Make sure that utils._import_all_the_way() gives back the most specific module.
        """
        module = utils._import_all_the_way('test_migration_packages.z.0001_test')
        self.assertEqual(module.__name__, 'test_migration_packages.z.0001_test')
