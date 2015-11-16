"""
Test the pulp.server.db.manage module.
"""
from argparse import Namespace
from cStringIO import StringIO
import os

from mock import call, inPy3k, MagicMock, patch
from mongoengine.queryset import DoesNotExist

from ... import base
from pulp.common.compat import all, json
from pulp.server.db import manage
from pulp.server.db.migrate import models
from pulp.server.db.model import MigrationTracker
import pulp.plugins.types.database as types_db
import migration_packages.a
import migration_packages.b
import migration_packages.duplicate_versions
import migration_packages.platform
import migration_packages.raise_exception
import migration_packages.version_gap
import migration_packages.version_zero
import migration_packages.z


# This is used for mocking
_test_type_json = '''{"types": [{
    "id" : "test_type_id",
    "display_name" : "Test Type",
    "description" : "Test Type",
    "unit_key" : ["attribute_1", "attribute_2", "attribute_3"],
    "search_indexes" : ["attribute_1", "attribute_3"]
}]}'''


# This is used to mock the entry_point system for discovering migration packages.
def iter_entry_points(name):
    class FakeEntryPoint(object):
        def __init__(self, migration_package):
            self._migration_package = migration_package

        def load(self):
            return self._migration_package

    test_packages = [
        migration_packages.a,
        migration_packages.duplicate_versions,
        migration_packages.raise_exception,
        migration_packages.version_gap,
        migration_packages.version_zero,
        migration_packages.z,
    ]

    if name == models.MIGRATIONS_ENTRY_POINT:
        return [FakeEntryPoint(package) for package in test_packages]
    return []


# Mock 1.0.0 has a built in mock_open, and one day when we upgrade to 1.0.0 we can use that. In the
# meantime, I've included the example for mock_open as listed in the Mock 0.8 docs, slightly
# modified to allow read_data to just be a str.
# http://www.voidspace.org.uk/python/mock/0.8/examples.html?highlight=open#mocking-open
if inPy3k:
    file_spec = [
        '_CHUNK_SIZE', '__enter__', '__eq__', '__exit__',
        '__format__', '__ge__', '__gt__', '__hash__', '__iter__', '__le__',
        '__lt__', '__ne__', '__next__', '__repr__', '__str__',
        '_checkClosed', '_checkReadable', '_checkSeekable',
        '_checkWritable', 'buffer', 'close', 'closed', 'detach',
        'encoding', 'errors', 'fileno', 'flush', 'isatty',
        'line_buffering', 'mode', 'name',
        'newlines', 'peek', 'raw', 'read', 'read1', 'readable',
        'readinto', 'readline', 'readlines', 'seek', 'seekable', 'tell',
        'truncate', 'writable', 'write', 'writelines']
else:
    file_spec = file


def mock_open(mock=None, read_data=None):
    if mock is None:
        mock = MagicMock(spec=file_spec)

    handle = MagicMock(spec=file_spec)
    handle.write.return_value = None
    fake_file = StringIO(read_data)
    if read_data is None:
        if hasattr(handle, '__enter__'):
            handle.__enter__.return_value = handle
    else:
        if hasattr(handle, '__enter__'):
            handle.__enter__.return_value = fake_file
        handle.read = fake_file.read
    mock.return_value = handle
    return mock


class MigrationTest(base.PulpServerTests):
    def clean(self):
        super(MigrationTest, self).clean()
        # Make sure each test doesn't have any lingering MigrationTrackers
        MigrationTracker.objects().delete()


class TestMigrateDatabase(MigrationTest):
    @patch('pulp.server.db.manage.logging.getLogger')
    @patch('pulp.server.db.migrate.models.get_migration_packages', auto_spec=True)
    def test_migration_removed(self, mock_get_packages, mock_getLogger):
        """
        ensure that if a migration raises the MigrationRemovedError, it bubbles up.
        """
        mock_package = MagicMock()
        mock_package.current_version = 6
        mock_package.latest_available_version = 7
        mock_package.name = 'foo'
        mock_migration = MagicMock()
        mock_migration.version = 7
        mock_package.unapplied_migrations = [mock_migration]
        e = models.MigrationRemovedError('0006', '1.2.0', '1.1.0', 'foo')
        mock_package.apply_migration.side_effect = e
        mock_get_packages.return_value = [mock_package]
        options = MagicMock()
        options.dry_run = False

        with self.assertRaises(models.MigrationRemovedError) as assertion:
            manage.migrate_database(options)

        self.assertTrue(assertion.exception is e)


class TestManageDB(MigrationTest):
    def clean(self):
        super(self.__class__, self).clean()
        types_db.clean()

    @patch.object(manage, 'PluginManager')
    @patch.object(manage, 'model')
    def test_ensure_database_indexes(self, mock_model, mock_plugin_manager):
        """
        Make sure that the ensure_indexes method is called for all
        the appropriate platform models
        """
        test_model = MagicMock()
        mock_plugin_manager.return_value.unit_models.itervalues.return_value = [test_model]
        manage.ensure_database_indexes()
        test_model.ensure_indexes.assert_called_once_with()

    @patch.object(manage, 'ensure_database_indexes')
    @patch('logging.config.fileConfig')
    @patch('pkg_resources.iter_entry_points', iter_entry_points)
    @patch('pulp.server.db.manage.connection.initialize')
    @patch('pulp.server.db.manage.factory')
    @patch('pulp.server.db.manage.logging.getLogger')
    @patch('pulp.server.db.manage.RoleManager.ensure_super_user_role')
    @patch('pulp.server.db.manage.managers.UserManager.ensure_admin')
    @patch('pulp.server.db.migrate.models.pulp.server.db.migrations',
           migration_packages.platform)
    @patch('sys.argv', ["pulp-manage-db"])
    @patch.object(models.MigrationPackage, 'apply_migration')
    def test_admin_is_ensured(self, apply_migration, ensure_admin, ensure_super_user_role,
                              getLogger, factory, initialize, fileConfig, ensure_db_indexes):
        """
        pulp-manage-db is responsible for making sure the admin user and role are in place. This
        test makes sure the manager methods that do that are called.
        """
        logger = MagicMock()
        getLogger.return_value = logger

        code = manage.main()

        self.assertEqual(code, os.EX_OK)

        # Make sure all the right logging happens
        expected_messages = ('Ensuring the admin role and user are in place.',
                             'Admin role and user are in place.')
        info_messages = ''.join([mock_call[1][0] for mock_call in logger.info.mock_calls])
        for msg in expected_messages:
            self.assertTrue(msg in info_messages)

        # Make sure the admin user and role creation methods were called. We'll leave it up to other
        # tests to make sure they work.
        ensure_admin.assert_called_once_with()
        ensure_super_user_role.assert_called_once_with()

        # Also, make sure the factory was initialized
        factory.initialize.assert_called_once_with()

        initialize.assert_called_once_with(max_timeout=1)

    @patch('logging.config.fileConfig')
    @patch('pulp.server.db.manage.logging.getLogger')
    @patch('pulp.server.db.manage._auto_manage_db')
    @patch('sys.argv', ["pulp-manage-db"])
    @patch('pulp.server.db.connection.initialize')
    def test_set_connection_timeout(self, mock_initialize, *unused_mocks):
        manage.main()

        mock_initialize.assert_called_once_with(max_timeout=1)

    @patch('sys.stderr')
    @patch('os.getuid', return_value=0)
    def test_wont_run_as_root(self, mock_getuid, mock_stderr):
        ret = manage.main()

        # make sure the exit code reflect a usage error
        self.assertEqual(ret, os.EX_USAGE)
        # make sure a message was written to stderr with appropriate keywords
        self.assertTrue(mock_stderr.write.call_count > 0)
        self.assertTrue('root' in mock_stderr.write.call_args_list[0][0][0])
        self.assertTrue('apache' in mock_stderr.write.call_args_list[0][0][0])

    @patch('pulp.server.db.manage.logging.getLogger')
    @patch('pkg_resources.iter_entry_points', iter_entry_points)
    @patch('pulp.server.db.manage.connection.initialize')
    @patch('pulp.server.db.migrate.models.pulp.server.db.migrations',
           migration_packages.platform)
    @patch('sys.argv', ["pulp-manage-db"])
    @patch('logging.config.fileConfig')
    def test_current_version_too_high(self, mocked_file_config, initialize, getLogger):
        """
        Set the current package version higher than latest available version, then sit back and eat
        popcorn.
        """
        logger = MagicMock()
        getLogger.return_value = logger

        # Make sure we start out with a clean slate
        self.assertEquals(MigrationTracker.objects().count(), 0)
        # Make sure that our mock works. There are four valid packages.
        self.assertEquals(len(models.get_migration_packages()), 5)
        # Set all versions to ridiculously high values
        for package in models.get_migration_packages():
            package._migration_tracker.version = 9999999
            package._migration_tracker.save()
        error_code = manage.main()
        self.assertEqual(error_code, os.EX_DATAERR)

        # There should have been a critical log about the Exception
        expected_messages = (
            'The database for migration package unit.server.db.migration_packages.'
            'platform is at version 9999999, which is larger than the latest version available, 1.')
        critical_messages = ''.join([mock_call[1][0] for mock_call in logger.critical.mock_calls])
        for msg in expected_messages:
            self.assertTrue(msg in critical_messages)

        initialize.assert_called_once_with(max_timeout=1)

    @patch('pulp.server.db.manage.logging.getLogger')
    @patch.object(models.MigrationPackage, 'apply_migration',
                  side_effect=models.MigrationPackage.apply_migration, autospec=True)
    @patch('pkg_resources.iter_entry_points', iter_entry_points)
    @patch('pulp.server.db.manage.connection.initialize')
    @patch('pulp.server.db.migrate.models.pulp.server.db.migrations',
           migration_packages.platform)
    @patch('sys.argv', ["pulp-manage-db"])
    @patch('logging.config.fileConfig')
    def test_migrate(self, mock_file_config, initialize, mocked_apply_migration, getLogger):
        """
        Let's set all the packages to be at version 0, and then check that the migrations get
        called in the correct order.
        """

        logger = MagicMock()
        getLogger.return_value = logger

        # Make sure we start out with a clean slate
        self.assertEquals(MigrationTracker.objects().count(), 0)
        # Make sure that our mock works. There are three valid packages.
        self.assertEquals(len(models.get_migration_packages()), 5)
        # Set all versions back to 0
        for package in models.get_migration_packages():
            package._migration_tracker.version = 0
            package._migration_tracker.save()
        manage.main()

        # There should have been a critical log about the Exception
        expected_messages = (
            'Applying migration '
            'unit.server.db.migration_packages.raise_exception.0002_oh_no failed.\n\n'
            'Halting migrations due to a migration failure.',
            "Bet you didn\'t see this coming."
        )
        critical_messages = ''.join([mock_call[1][0] for mock_call in logger.critical.mock_calls])
        for msg in expected_messages:
            self.assertTrue(msg in critical_messages)

        migration_modules_called = [
            mock_call[1][1].name for mock_call in mocked_apply_migration.mock_calls]
        # Note that none of the migrations that don't meet our criteria show up in this list. Also,
        # Note that migration_packages.raise_exception.0003_shouldnt_run doesn't appear
        # since migration_packages.raise_exception.0002_oh_no raised an Exception. Note
        # also that even though the raise_exception package raised an Exception, we still run all
        # the z migrations because we don't want one package to break another.
        expected_migration_modules_called = [
            'unit.server.db.migration_packages.platform.0001_stuff_and_junk',
            'unit.server.db.migration_packages.raise_exception.0001_works_fine',
            'unit.server.db.migration_packages.raise_exception.0002_oh_no']
        self.assertEquals(migration_modules_called, expected_migration_modules_called)
        # Assert that our precious versions have been updated correctly
        for package in models.get_migration_packages():
            if package.name == 'unit.server.db.migration_packages.platform':
                self.assertEqual(package.current_version, package.latest_available_version)
            elif package.name == 'unit.server.db.migration_packages.raise_exception':
                # The raised Exception should have prevented us from getting past version 1
                self.assertEquals(package.current_version, 1)
            else:
                # raise_exception should cause the migrations to stop
                self.assertEqual(package.current_version, 0)

        initialize.assert_called_once_with(max_timeout=1)

    @patch('sys.stderr')
    @patch('sys.stdout')
    @patch('pkg_resources.iter_entry_points', iter_entry_points)
    @patch('pulp.server.db.migrate.models.pulp.server.db.migrations',
           migration_packages.platform)
    @patch('sys.argv', ["pulp-manage-db"])
    @patch('pulp.server.db.manage._logger')
    @patch('pulp.server.db.manage._start_logging')
    @patch('pulp.server.db.manage.connection.initialize')
    def test_migrate_with_new_packages(self, initialize, start_logging_mock, logger_mock,
                                       mocked_stdout, mocked_stderr):
        """
        Adding new packages to a system that doesn't have any trackers should advance
        each package to the latest available version, applying no migrate() functions along the
        way.
        """
        # Make sure we start out with a clean slate
        self.assertEquals(MigrationTracker.objects().count(), 0)
        # Make sure that our mock works. There are five valid packages.
        self.assertEquals(len(models.get_migration_packages()), 5)
        manage.main()

        for package in models.get_migration_packages():
            if 'raise_exception' in str(package):
                # The Exception raising package should get to version 3, despite the fact that
                # version 2 raises an exception, because new trackers get fast-forwarded.
                self.assertEqual(package.current_version, 3)
            else:
                # All other packages should reach their top versions
                self.assertEqual(package.current_version, package.latest_available_version)

        initialize.assert_called_once_with(max_timeout=1)

    @patch('pulp.plugins.types.database._drop_indexes')
    @patch('__builtin__.open', mock_open(read_data=_test_type_json))
    @patch('os.listdir', return_value=['test_type.json'])
    @patch('sys.argv', ["pulp-manage-db"])
    @patch('sys.stdout', MagicMock())
    @patch('pulp.server.db.manage._start_logging')
    @patch('pulp.server.db.manage.connection.initialize')
    def test_pulp_manage_db_loads_types(self, initialize, start_logging_mock, listdir_mock,
                                        mock_drop_indices):
        """
        Test calling pulp-manage-db imports types on a clean types database.
        """
        manage.main()

        all_collection_names = types_db.all_type_collection_names()
        self.assertFalse(mock_drop_indices.called)
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
        indexes = collection.index_information()
        self.assertEqual(indexes['_id_']['key'], [(u'_id', 1)])
        # Make sure we have the unique constraint on all three attributes
        self.assertEqual(indexes['attribute_1_1_attribute_2_1_attribute_3_1']['unique'], True)
        self.assertEqual(indexes['attribute_1_1_attribute_2_1_attribute_3_1']['dropDups'], False)
        self.assertEqual(indexes['attribute_1_1_attribute_2_1_attribute_3_1']['key'],
                         [(u'attribute_1', 1), (u'attribute_2', 1), (u'attribute_3', 1)])
        # Make sure we indexes attributes 1 and 3
        self.assertEqual(indexes['attribute_1_1']['dropDups'], False)
        self.assertEqual(indexes['attribute_1_1']['key'], [(u'attribute_1', 1)])
        self.assertEqual(indexes['attribute_3_1']['dropDups'], False)
        self.assertEqual(indexes['attribute_3_1']['key'], [(u'attribute_3', 1)])
        # Make sure we only have the indexes that we've hand inspected here
        self.assertEqual(indexes.keys(), [u'_id_', u'attribute_1_1_attribute_2_1_attribute_3_1',
                                          u'attribute_1_1', u'attribute_3_1'])

        initialize.assert_called_once_with(max_timeout=1)

    @patch('pulp.server.db.manage.logging.getLogger')
    @patch.object(models.MigrationPackage, 'apply_migration',
                  side_effect=models.MigrationPackage.apply_migration, autospec=True)
    @patch('pkg_resources.iter_entry_points', iter_entry_points)
    @patch('pulp.server.db.manage.connection.initialize')
    @patch('pulp.server.db.migrate.models.pulp.server.db.migrations',
           migration_packages.platform)
    @patch('sys.argv', ["pulp-manage-db", "--test"])
    @patch('logging.config.fileConfig')
    def test_migrate_with_test_flag(self, mock_file_config, initialize, mocked_apply_migration,
                                    getLogger):
        """
        Let's set all the packages to be at version 0, and then check that the migrations get called
        in the correct order. We will also set the --test flag and ensure that the migration
        versions do not get updated.
        """

        logger = MagicMock()
        getLogger.return_value = logger

        # Make sure we start out with a clean slate
        self.assertEquals(MigrationTracker.objects().count(), 0)
        # Make sure that our mock works. There are five valid packages.
        self.assertEquals(len(models.get_migration_packages()), 5)
        # Set all versions back to 0
        for package in models.get_migration_packages():
            package._migration_tracker.version = 0
            package._migration_tracker.save()
        manage.main()

        # There should have been a critical log about the Exception
        expected_messages = (
            'Applying migration '
            'unit.server.db.migration_packages.raise_exception.0002_oh_no failed.\n\n'
            'Halting migrations due to a migration failure.',
            'Bet you didn\'t see this coming.'
        )
        critical_messages = [mock_call[1][0] for mock_call in logger.critical.mock_calls]
        for msg in expected_messages:
            self.assertTrue(msg in critical_messages)

        migration_modules_called = [
            mock_call[1][1].name for mock_call in mocked_apply_migration.mock_calls]
        # Note that none of the migrations that don't meet our criteria show up in this list. Also,
        # Note that migration_packages.raise_exception.0003_shouldnt_run doesn't appear
        # since migration_packages.raise_exception.0002_oh_no raised an Exception. Note
        # also that even though the raise_exception package raised an Exception, we still run all
        # the z migrations because we don't want one package to break another.
        expected_migration_modules_called = [
            'unit.server.db.migration_packages.platform.0001_stuff_and_junk',
            'unit.server.db.migration_packages.raise_exception.0001_works_fine',
            'unit.server.db.migration_packages.raise_exception.0002_oh_no']
        self.assertEquals(migration_modules_called, expected_migration_modules_called)
        # Assert that our precious versions have not been updated, since we have the --test flag
        for package in models.get_migration_packages():
            self.assertEqual(package.current_version, 0)

        initialize.assert_called_once_with(max_timeout=1)

    @patch('pulp.server.db.manage.logging.getLogger')
    @patch.object(models.MigrationPackage, 'apply_migration',
                  side_effect=models.MigrationPackage.apply_migration, autospec=True)
    @patch('pkg_resources.iter_entry_points', iter_entry_points)
    @patch('pulp.server.db.manage.connection.initialize')
    @patch('pulp.server.db.migrate.models.pulp.server.db.migrations',
           migration_packages.platform)
    @patch('sys.argv', ["pulp-manage-db", "--dry-run"])
    @patch('logging.config.fileConfig')
    def test_migrate_with_dry_run_flag(self, mock_file_config, initialize, mocked_apply_migration,
                                       getLogger):
        """
        Test that when a dry run is performed, no migrations actually occur.
        """
        logger = MagicMock()
        getLogger.return_value = logger

        # Make sure we start out with a clean slate
        self.assertEquals(MigrationTracker.objects().count(), 0)
        # Make sure that our mock works. There are three valid packages.
        self.assertEquals(len(models.get_migration_packages()), 5)
        # Set all versions back to 0
        for package in models.get_migration_packages():
            package._migration_tracker.version = 0
            package._migration_tracker.save()
        result = manage.main()

        # Test that none of the mock objects were actually called
        migration_modules_called = [
            mock_call[1][1].name for mock_call in mocked_apply_migration.mock_calls]
        self.assertEquals(0, len(migration_modules_called))
        self.assertEquals(1, result)
        for package in models.get_migration_packages():
            self.assertEqual(package.current_version, 0)

        initialize.assert_called_once_with(max_timeout=1)

    @patch('pulp.server.db.manage.connection.initialize')
    @patch('pulp.server.db.manage.RoleManager.ensure_super_user_role')
    @patch('pulp.server.db.manage.managers.UserManager.ensure_admin')
    @patch('pulp.server.db.manage.logging.getLogger')
    @patch.object(models.MigrationPackage, 'apply_migration',
                  side_effect=models.MigrationPackage.apply_migration, autospec=True)
    @patch('pkg_resources.iter_entry_points', iter_entry_points)
    @patch('pulp.server.db.migrate.models.pulp.server.db.migrations',
           migration_packages.platform)
    @patch('sys.argv', ["pulp-manage-db", "--dry-run"])
    @patch('logging.config.fileConfig')
    def test_admin_creation_dry_run(self, mock_file_config, mocked_apply_migration, getLogger,
                                    mock_ensure_admin, mock_ensure_super_role, initialize):
        logger = MagicMock()
        getLogger.return_value = logger

        exit_code = manage.main()

        self.assertEqual(exit_code, 1)

        # Make sure the admin user and role creation methods were not called
        self.assertEquals(0, mock_ensure_admin.call_count)
        self.assertEquals(0, mock_ensure_super_role.call_count)
        initialize.assert_called_once_with(max_timeout=1)

    @patch.object(manage, 'ensure_database_indexes')
    @patch('pulp.server.db.manage.logging.getLogger')
    @patch.object(models.MigrationPackage, 'apply_migration',
                  side_effect=models.MigrationPackage.apply_migration, autospec=True)
    @patch('pkg_resources.iter_entry_points')
    @patch('pulp.server.db.manage.connection.initialize')
    @patch('pulp.server.db.migrate.models.pulp.server.db.migrations',
           migration_packages.platform)
    @patch('pulp.server.db.manage.parse_args', autospec=True)
    @patch('logging.config.fileConfig')
    def test_dry_run_no_changes(self, mock_file_config, mock_parse_args, initialize,
                                mocked_apply_migration, mock_entry, getLogger, mock_ensure_indexes):
        logger = MagicMock()
        getLogger.return_value = logger
        mock_args = Namespace(dry_run=True, test=False)
        mock_parse_args.return_value = mock_args

        # Test that when dry run is on, it returns 1 if migrations remain
        exit_code = manage.main()
        self.assertEqual(exit_code, 1)
        self.assertFalse(mock_ensure_indexes.called)
        initialize.assert_called_once_with(max_timeout=1)

        # Actually apply the migrations
        mock_args.dry_run = False
        mock_ensure_indexes.reset_mock()
        initialize.reset_mock()
        exit_code = manage.main()
        self.assertEqual(exit_code, 0)
        self.assertTrue(mock_ensure_indexes.called)
        initialize.assert_called_once_with(max_timeout=1)

        # Perform another dry run and check the return value is now 0
        mock_args.dry_run = True
        mock_ensure_indexes.reset_mock()
        initialize.reset_mock()
        exit_code = manage.main()
        self.assertEquals(exit_code, 0)
        self.assertFalse(mock_ensure_indexes.called)
        initialize.assert_called_once_with(max_timeout=1)

    @patch('pulp.server.db.manage.logging.getLogger')
    @patch('pulp.server.db.manage.connection.initialize')
    @patch('pulp.server.db.manage.parse_args', autospec=True)
    @patch.object(manage, '_auto_manage_db')
    def test_migration_removed(self, mock_auto_manage_db, mock_parse_args, mock_init,
                               mock_getLogger):
        e = models.MigrationRemovedError('0002', '1.2.0', '1.1.0', 'foo')
        mock_auto_manage_db.side_effect = e

        ret = manage.main()
        self.assertEqual(ret, os.EX_SOFTWARE)


class TestMigrationModule(MigrationTest):
    def test___cmp__(self):
        mm_2 = models.MigrationModule('unit.server.db.migration_packages.z.0002_test')
        mm_3 = models.MigrationModule('unit.server.db.migration_packages.z.0003_test')
        self.assertEquals(cmp(mm_2, mm_3), -1)

    def test___init__(self):
        mm = models.MigrationModule('unit.server.db.migration_packages.z.0002_test')
        self.assertEquals(mm._module.__name__,
                          'unit.server.db.migration_packages.z.0002_test')
        self.assertEquals(mm.version, 2)
        # It should have a migrate attribute that is callable
        self.assertTrue(hasattr(mm.migrate, '__call__'))

    def test___repr__(self):
        mm = models.MigrationModule('unit.server.db.migration_packages.z.0003_test')
        self.assertEqual(repr(mm), 'unit.server.db.migration_packages.z.0003_test')

    def test__get_version(self):
        mm = models.MigrationModule('unit.server.db.migration_packages.z.0003_test')
        self.assertEquals(mm._get_version(), 3)

    def test_name(self):
        mm = models.MigrationModule('unit.server.db.migration_packages.z.0003_test')
        self.assertEqual(mm.name, 'unit.server.db.migration_packages.z.0003_test')


class TestMigrationPackage(MigrationTest):
    def test___init__(self):
        mp = models.MigrationPackage(migration_packages.z)
        self.assertEquals(mp._package.__name__, 'unit.server.db.migration_packages.z')
        self.assertEquals(mp._migration_tracker.name, 'unit.server.db.migration_packages.z')
        # By default, MigrationPackages should start at version -1
        self.assertEquals(mp._migration_tracker.version, -1)

    @patch('pulp.server.db.migrate.models.MigrationTracker')
    def test__init__2(self, mock_tracker):
        """
        Test package does not exist.
        """
        mock_tracker.objects.return_value.get.side_effect = DoesNotExist()
        models.MigrationPackage(migration_packages.b)
        self.assertEqual(mock_tracker.return_value.save.call_count, 1)

    @patch('pulp.server.db.migrate.models.MigrationTracker')
    def test__init__3(self, mock_tracker):
        """
        Test package exists.
        """
        mock_some = MagicMock()
        mock_tracker.objects.return_value.get = mock_some
        models.MigrationPackage(migration_packages.a)
        self.assertEqual(mock_tracker.return_value.save.call_count, 0)

    def test_apply_migration(self):
        mp = models.MigrationPackage(migration_packages.z)
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
        mp = models.MigrationPackage(migration_packages.z)
        self.assertEquals(mp.available_versions, [1, 2, 3])

    def test_current_version(self):
        mp = models.MigrationPackage(migration_packages.z)
        # By default, a MigrationPackage will be at version -1
        self.assertEqual(mp.current_version, -1)
        # Now let's change the version to 4 and see what happens
        mp._migration_tracker.version = 4
        mp._migration_tracker.save()
        # Now we should be able to reinstantiate this mammajamma and see that the version is right
        mp = models.MigrationPackage(migration_packages.z)
        self.assertEqual(mp.current_version, 4)

    def test_duplicate_versions(self):
        error_message = 'There are two migration modules that share version 2 in ' +\
            'unit.server.db.migration_packages.duplicate_versions.'
        try:
            models.MigrationPackage(migration_packages.duplicate_versions)
            self.fail('The MigrationPackage.DuplicateVersions exception should have been raised, '
                      'but was not raised.')
        except models.MigrationPackage.DuplicateVersions, e:
            self.assertEquals(str(e), error_message)

    def test_latest_available_version(self):
        # This one has no migrations, so the latest is 0
        self.assertEqual(
            models.MigrationPackage(migration_packages.a).latest_available_version, 0)
        self.assertEqual(models.MigrationPackage(
                         migration_packages.platform).latest_available_version, 1)
        self.assertEqual(
            models.MigrationPackage(migration_packages.z).latest_available_version, 3)

    def test_migrations(self):
        migration_package = models.MigrationPackage(migration_packages.z)
        migrations = migration_package.migrations
        self.assertEqual(len(migrations), 3)
        self.assertTrue(all([isinstance(migration, models.MigrationModule)
                        for migration in migrations]))
        # Make sure their versions are set and sorted appropriately
        self.assertEqual([1, 2, 3], [migration.version for migration in migrations])
        # Check the names
        self.assertEqual(['unit.server.db.migration_packages.z.0001_test',
                          'unit.server.db.migration_packages.z.0002_test',
                          'unit.server.db.migration_packages.z.0003_test'],
                         [migration._module.__name__ for migration in migrations])

    def test_name(self):
        mp = models.MigrationPackage(migration_packages.z)
        self.assertEqual(mp.name, 'unit.server.db.migration_packages.z')

    @patch('pulp.server.db.migrate.models._logger.debug')
    def test_nonconforming_modules(self, log_mock):
        # The z package has a module called doesnt_conform_to_naming_convention.py. This shouldn't
        # count as a migration module, but it also should not interfere with the existing migration
        # modules, and the debug log should mention that the file was found but was not found to be
        # a migration module. The z package also has a module called 0004_doesnt_have_migrate.py.
        # Since it doesn't have a migrate function, it should just be logged and things should keep
        # going as usual.
        mp = models.MigrationPackage(migration_packages.z)
        migrations = mp.migrations
        self.assertEqual(len(migrations), 3)
        self.assertTrue(all([isinstance(migration, models.MigrationModule)
                        for migration in migrations]))
        # Make sure their versions are set and sorted appropriately
        self.assertEqual([1, 2, 3], [migration.version for migration in migrations])
        # Check the names
        self.assertEqual(['unit.server.db.migration_packages.z.0001_test',
                          'unit.server.db.migration_packages.z.0002_test',
                          'unit.server.db.migration_packages.z.0003_test'],
                         [migration.name for migration in migrations])
        # Now let's assert that the non-conforming dealios were logged
        # They actually get logged twice each, once for when we initialized the MP, and the other
        # when we retrieved the migrations
        log_mock.assert_has_calls([
            call('The module unit.server.db.migration_packages.z.0004_doesnt_have_migrate '
                 'doesn\'t have a migrate function. It will be ignored.'),
            call('The module '
                 'unit.server.db.migration_packages.z.doesnt_conform_to_naming_convention '
                 'doesn\'t conform to the migration package naming conventions. It will be '
                 'ignored.'),
            call('The module unit.server.db.migration_packages.z.0004_doesnt_have_migrate '
                 'doesn\'t have a migrate function. It will be ignored.'),
            call('The module '
                 'unit.server.db.migration_packages.z.doesnt_conform_to_naming_convention '
                 'doesn\'t conform to the migration package naming conventions. It will be '
                 'ignored.')])

    def test_unapplied_migrations(self):
        mp = models.MigrationPackage(migration_packages.z)
        # Drop the version to 1, which should make this method return two migrations
        mp._migration_tracker.version = 1
        mp._migration_tracker.save()
        unapplied = mp.unapplied_migrations
        self.assertEqual(len(unapplied), 2)
        self.assertEqual([m.version for m in unapplied], [2, 3])
        self.assertEqual(
            [m._module.__name__ for m in unapplied],
            ['unit.server.db.migration_packages.z.0002_test',
             'unit.server.db.migration_packages.z.0003_test'])

    def test_migration_version_cant_be_zero(self):
        """
        Make sure that we reserve migration zero.
        """
        error_message = (
            '0 is a reserved migration version number, but the module '
            'unit.server.db.migration_packages.version_zero.0000_not_allowed has been '
            'assigned that version.')
        try:
            models.MigrationPackage(migration_packages.version_zero)
            self.fail('The MigrationPackage.DuplicateVersions exception should have been raised, '
                      'but was not raised.')
        except models.MigrationPackage.DuplicateVersions, e:
            self.assertEquals(str(e), error_message)

    def test_migration_version_gap(self):
        """
        Make sure that we allow migrations to have version gaps. Previously version gaps were not
        allowed, and this call would have caused a validation failure. This test makes sure no such
        failure happens.
        """
        models.MigrationPackage(migration_packages.version_gap)

    @patch('pulp.server.db.migrate.models.pulp.server.db.migrations',
           migration_packages.platform)
    def test___cmp__(self):
        mp_1 = models.MigrationPackage(migration_packages.a)
        mp_2 = models.MigrationPackage(migration_packages.platform)
        mp_3 = models.MigrationPackage(migration_packages.z)
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

    def test___repr__(self):
        mp = models.MigrationPackage(migration_packages.z)
        self.assertEqual(repr(mp), 'unit.server.db.migration_packages.z')

    def test___str__(self):
        mp = models.MigrationPackage(migration_packages.z)
        self.assertEqual(str(mp), 'unit.server.db.migration_packages.z')


class TestMigrationUtils(MigrationTest):
    def test__import_all_the_way(self):
        """
        Make sure that models._import_all_the_way() gives back the most specific module.
        """
        module = models._import_all_the_way('unit.server.db.migration_packages.z.0001_test')
        self.assertEqual(module.__name__, 'unit.server.db.migration_packages.z.0001_test')

    @patch('pkg_resources.iter_entry_points', iter_entry_points)
    @patch('pulp.server.db.migrate.models.pulp.server.db.migrations',
           migration_packages.platform)
    @patch('pulp.server.db.migrate.models._logger.error')
    def test_get_migration_packages(self, log_mock):
        """
        Ensure that pulp.server.db.migrate.models.get_migration_packages functions correctly.
        """
        packages = models.get_migration_packages()
        self.assertEquals(len(packages), 5)
        self.assertTrue(
            all([isinstance(package, models.MigrationPackage) for package in packages]))
        # Make sure that the packages are sorted correctly, with platform first
        self.assertEquals(packages[0].name, 'unit.server.db.migration_packages.platform')
        self.assertEquals(packages[1].name, 'unit.server.db.migration_packages.a')
        self.assertEquals(packages[2].name,
                          'unit.server.db.migration_packages.raise_exception')
        self.assertEquals(packages[3].name, 'unit.server.db.migration_packages.version_gap')
        self.assertEquals(packages[4].name, 'unit.server.db.migration_packages.z')
        # Assert that we logged the duplicate version exception and the version gap exception
        expected_log_calls = [call('There are two migration modules that share version 2 in '
                              'unit.server.db.migration_packages.duplicate_versions.')]
        log_mock.assert_has_calls(expected_log_calls)
