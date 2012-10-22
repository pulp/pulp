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

from mock import MagicMock, mock_open, patch

from pulp.common.compat import json
from pulp.server.db import manage
from pulp.server.db.migrate import utils
from pulp.server.db.model.migration_tracker import MigrationTracker
from pulp.server.managers.migration_tracker import DoesNotExist, MigrationTrackerManager
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
        super(MigrationTest, self).clean()
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


class TestMigrationModule(MigrationTest):
    def test___init__(self):
        mm = utils.MigrationModule('test_migration_packages.z.0002_test')
        self.assertEquals(mm._module.__name__, 'test_migration_packages.z.0002_test')
        self.assertEquals(mm.version, 2)
        # It should have a migrate attribute that is callable
        self.assertTrue(hasattr(mm.migrate, '__call__'))

    def test__get_version(self):
        mm = utils.MigrationModule('test_migration_packages.z.0003_test')
        self.assertEquals(mm._get_version(), 3)

    def test___cmp__(self):
        mm_2 = utils.MigrationModule('test_migration_packages.z.0002_test')
        mm_3 = utils.MigrationModule('test_migration_packages.z.0003_test')
        self.assertEquals(cmp(mm_2, mm_3), -1)


class TestMigrationPackage(MigrationTest):
    def test___init__(self):
        mp = utils.MigrationPackage('test_migration_packages.z')
        self.assertEquals(mp._package.__name__, 'test_migration_packages.z')
        self.assertEquals(mp._migration_tracker.name, 'test_migration_packages.z')
        # We auto update to the latest version since this is a new package
        self.assertEquals(mp._migration_tracker.version, 3)

    def test_apply_migration(self):
        mp = utils.MigrationPackage('test_migration_packages.z')
        # Let's fake the migration version being at 2 instead of 3
        mp._migration_tracker.version = 2
        mp._migration_tracker.save()
        # Now, let's apply version 3
        mm_v3 = mp.unapplied_migrations[-1]
        self.assertEqual(mm_v3.version, 3)
        # Let's change the migrate() function to one that tracks that it gets called.
        mm_v3.migrate = MagicMock(name='migrate')
        self.assertEquals(mm_v3.migrate.called, False)
        # Now try to run the migration and assert that it gets called
        mp.apply_migration(mm_v3)
        self.assertEquals(mm_v3.migrate.called, True)
        # Now the mp should be at v3
        self.assertEqual(mp.current_version, 3)

    def test_available_versions(self):
        mp = utils.MigrationPackage('test_migration_packages.z')
        self.assertEquals(mp.available_versions, [1, 2, 3])

    def test_current_version(self):
        mp = utils.MigrationPackage('test_migration_packages.z')
        self.assertEqual(mp.current_version, 3)
        # Now let's change the version to 4 and see what happens
        mp._migration_tracker.version = 4
        mp._migration_tracker.save()
        # Now we should be able to reinstantiate this mammajamma and see that the version is right
        mp = utils.MigrationPackage('test_migration_packages.z')
        self.assertEqual(mp.current_version, 4)

    def test_latest_available_version(self):
        # This one has no migrations, so the latest is 0
        self.assertEqual(
            utils.MigrationPackage('test_migration_packages.a').latest_available_version, 0)
        self.assertEqual(
            utils.MigrationPackage('test_migration_packages.platform').latest_available_version, 1)
        self.assertEqual(
            utils.MigrationPackage('test_migration_packages.z').latest_available_version, 3)

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

    def test_name(self):
        mp = utils.MigrationPackage('test_migration_packages.z')
        self.assertEqual(mp.name, 'test_migration_packages.z')

    @patch('pulp.server.db.migrate.utils.logger.debug')
    def test_nonconforming_module_names(self, log_mock):
        # The z package has a module called doesnt_conform_to_naming_convention.py. This shouldn't
        # count as a migration module, but it also should not interfere with the existing migration
        # modules, and the debug log should mention that the file was found but was not found to be
        # a migration module
        mp = utils.MigrationPackage('test_migration_packages.z')
        migrations = mp.migrations
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
        # Now let's assert that the non-conforming dealio was logged
        log_mock.assert_called_with('The module '
            'test_migration_packages.z.doesnt_conform_to_naming_convention doesn\'t conform to '
            'the migration package naming conventions. It will be ignored.')

    def test_unapplied_migrations(self):
        mp = utils.MigrationPackage('test_migration_packages.z')
        # Drop the version to 1, which should make this method return two migrations
        mp._migration_tracker.version = 1
        mp._migration_tracker.save()
        unapplied = mp.unapplied_migrations
        self.assertEqual(len(unapplied), 2)
        self.assertEqual([m.version for m in unapplied], [2, 3])
        self.assertEqual([m._module.__name__ for m in unapplied],
            ['test_migration_packages.z.0002_test', 'test_migration_packages.z.0003_test'])

    @patch('pulp.server.db.migrate.utils.pulp.server.db.migrations.platform',
           test_migration_packages.platform)
    def test___cmp__(self):
        mp_1 = utils.MigrationPackage('test_migration_packages.a')
        mp_2 = utils.MigrationPackage('test_migration_packages.platform')
        mp_3 = utils.MigrationPackage('test_migration_packages.z')
        # platform should always sort first, and they should otherwise be alphabeticalness
        self.assertEqual(cmp(mp_1, mp_1), 0)
        self.assertEqual(cmp(mp_1, mp_2), 1)
        self.assertEqual(cmp(mp_1, mp_3), -1)
        self.assertEqual(cmp(mp_2, mp_1), -1)
        self.assertEqual(cmp(mp_2, mp_2), 0)
        self.assertEqual(cmp(mp_2, mp_3), -1)
        self.assertEqual(cmp(mp_3, mp_1), 1)
        self.assertEqual(cmp(mp_3, mp_2), 1)
        self.assertEqual(cmp(mp_3, mp_3), 0)

    def test___str__(self):
        mp = utils.MigrationPackage('test_migration_packages.z')
        self.assertEqual(str(mp), 'test_migration_packages.z')

    def test___repr__(self):
        mp = utils.MigrationPackage('test_migration_packages.z')
        self.assertEqual(repr(mp), 'test_migration_packages.z')


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


class TestMigrationTrackerManager(MigrationTest):
    def setUp(self):
        super(self.__class__, self).setUp()
        self.mtm = MigrationTrackerManager()

    def test___init__(self):
        self.assertEquals(self.mtm._collection, MigrationTracker.get_collection())

    def test_create(self):
        mt = self.mtm.create('first_prime', 2)
        self.assertEquals(mt.name, 'first_prime')
        self.assertEquals(mt.version, 2)
        # Make sure the DB got to the correct state
        self.assertEquals(mt._collection.find({}).count(), 1)
        mt_bson = mt._collection.find_one({'name': 'first_prime'})
        self.assertEquals(mt_bson['name'], 'first_prime')
        self.assertEquals(mt_bson['version'], 2)

    def test_get(self):
        self.mtm.create('only_even_prime', 2)
        mt = self.mtm.get('only_even_prime')
        self.assertEquals(mt.name, 'only_even_prime')
        self.assertEquals(mt.version, 2)
        # Now try to get one that doesn't exist
        try:
            self.mtm.get("doesn't exist")
            self.fail("The get() should have raised DoesNotExist, but did not.")
        except DoesNotExist:
            # This is the expected behavior
            pass

    def test_get_or_create(self):
        # Insert one for getting
        self.mtm.create('smallest_perfect_number', 6)
        # Now get or create it with an incorrect version. The incorrect version should not be set
        mt = self.mtm.get_or_create('smallest_perfect_number', defaults={'version': 7})
        self.assertEquals(mt.name, 'smallest_perfect_number')
        self.assertEquals(mt.version, 6) # not 7
        mt_bson = mt._collection.find_one({'name': 'smallest_perfect_number'})
        self.assertEquals(mt_bson['name'], 'smallest_perfect_number')
        self.assertEquals(mt_bson['version'], 6)
        # This will cause a create
        self.assertEquals(mt._collection.find({'name': 'x^y=y^x'}).count(), 0)
        # 16 is the only number for which x^y = y^x, where x != y
        mt = self.mtm.get_or_create('x^y=y^x', defaults={'version': 16})
        self.assertEquals(mt._collection.find({'name': 'x^y=y^x'}).count(), 1)
        self.assertEquals(mt.name, 'x^y=y^x')
        self.assertEquals(mt.version, 16)
        mt_bson = mt._collection.find_one({'name': 'x^y=y^x'})
        self.assertEquals(mt_bson['name'], 'x^y=y^x')
        self.assertEquals(mt_bson['version'], 16)


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
