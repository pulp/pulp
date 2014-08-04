import datetime
import os
import shutil
import signal

import mock

from .... import base
from pulp.common import dateutils, constants
from pulp.devel import mock_plugins
from pulp.plugins.model import SyncReport
from pulp.server.async import tasks
from pulp.server.db.model.repository import Repo, RepoImporter, RepoSyncResult
from pulp.server.exceptions import PulpExecutionException, InvalidValue
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.importer as repo_importer_manager
import pulp.server.managers.repo.publish as repo_publish_manager
import pulp.server.managers.repo.sync as repo_sync_manager


class MockRepoPublishManager:

    # Last call state
    repo_id = None
    base_progress_report = None

    # Call behavior
    raise_error = False

    def validate_config(self, repo_data, distributor_config):
        return True

    def auto_publish_for_repo(self, repo_id, base_progress_report):
        MockRepoPublishManager.repo_id = repo_id
        MockRepoPublishManager.base_progress_report = base_progress_report

        if MockRepoPublishManager.raise_error:
            raise repo_publish_manager.PulpExecutionException(repo_id)

    @classmethod
    def reset(cls):
        MockRepoPublishManager.repo_id = None
        MockRepoPublishManager.raise_error = False


class RepoSyncManagerTests(base.PulpServerTests):

    def setUp(self):
        super(RepoSyncManagerTests, self).setUp()
        mock_plugins.install()

        # Create the manager instances for testing
        self.repo_manager = repo_manager.RepoManager()
        self.importer_manager = repo_importer_manager.RepoImporterManager()
        self.sync_manager = repo_sync_manager.RepoSyncManager()

    def tearDown(self):
        super(RepoSyncManagerTests, self).tearDown()
        mock_plugins.reset()

        # Reset the manager factory
        manager_factory.reset()

    def clean(self):
        super(RepoSyncManagerTests, self).clean()
        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoSyncResult.get_collection().remove()

        # Reset the state of the mock's tracker variables
        MockRepoPublishManager.reset()

    @mock.patch('pulp.server.managers.event.fire.EventFireManager.fire_repo_sync_started')
    @mock.patch('pulp.server.managers.event.fire.EventFireManager.fire_repo_sync_finished')
    def test_sync(self, mock_finished, mock_started):
        """
        Tests sync under normal conditions where everything is configured
        correctly. No importer config is specified.
        """

        # Setup
        sync_config = {'bruce' : 'hulk', 'tony' : 'ironman'}
        self.repo_manager.create_repo('repo-1')
        self.importer_manager.set_importer('repo-1', 'mock-importer', sync_config)

        # Test
        self.sync_manager.sync('repo-1', sync_config_override=None)

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'repo-1'})
        repo_importer = RepoImporter.get_collection().find_one({'repo_id' : 'repo-1', 'id' : 'mock-importer'})

        #   Database
        self.assertTrue(repo_importer['last_sync'] is not None)
        self.assertTrue(assert_last_sync_time(repo_importer['last_sync']))

        #   Call into the Importer
        sync_args = mock_plugins.MOCK_IMPORTER.sync_repo.call_args[0]

        self.assertEqual(repo['id'], sync_args[0].id)
        self.assertTrue(sync_args[1] is not None)
        self.assertEqual({}, sync_args[2].plugin_config)
        self.assertEqual(sync_config, sync_args[2].repo_plugin_config)
        self.assertEqual({}, sync_args[2].override_config)

        #   History Entry
        history = list(RepoSyncResult.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(1, len(history))
        self.assertEqual('repo-1', history[0]['repo_id'])
        self.assertEqual(RepoSyncResult.RESULT_SUCCESS, history[0]['result'])
        self.assertEqual('mock-importer', history[0]['importer_id'])
        self.assertEqual('mock-importer', history[0]['importer_type_id'])
        self.assertTrue(history[0]['started'] is not None)
        self.assertTrue(history[0]['completed'] is not None)

        self.assertEqual(10, history[0]['added_count'])
        self.assertEqual(1, history[0]['removed_count'])
        self.assertTrue(history[0]['summary'] is not None)
        self.assertTrue(history[0]['details'] is not None)

        self.assertTrue(history[0]['error_message'] is None)
        self.assertTrue(history[0]['exception'] is None)
        self.assertTrue(history[0]['traceback'] is None)

        self.assertEqual(1, mock_started.call_count)
        self.assertEqual('repo-1', mock_started.call_args[0][0])

        self.assertEqual(1, mock_finished.call_count)
        self.assertEqual('repo-1', mock_finished.call_args[0][0]['repo_id'])

    def test_sync_with_graceful_fail(self):
        # Setup
        sync_config = {'bruce' : 'hulk', 'tony' : 'ironman'}
        self.repo_manager.create_repo('repo-1')
        self.importer_manager.set_importer('repo-1', 'mock-importer', sync_config)

        mock_plugins.MOCK_IMPORTER.sync_repo.return_value = SyncReport(False, 10, 5, 1, 'Summary of the sync', 'Details of the sync')

        # Test
        self.assertRaises(PulpExecutionException, self.sync_manager.sync, 'repo-1')

        # Verify
        history = list(RepoSyncResult.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(1, len(history))
        self.assertEqual('repo-1', history[0]['repo_id'])
        self.assertEqual(RepoSyncResult.RESULT_FAILED, history[0]['result'])
        self.assertEqual('mock-importer', history[0]['importer_id'])
        self.assertEqual('mock-importer', history[0]['importer_type_id'])
        self.assertTrue(history[0]['started'] is not None)
        self.assertTrue(history[0]['completed'] is not None)

        # Cleanup
        mock_plugins.reset()

    def test_sync_with_sync_config_override(self):
        """
        Tests a sync when passing in an individual config of override options.
        """

        # Setup
        importer_config = {'thor' : 'thor'}
        self.repo_manager.create_repo('repo-1')
        self.importer_manager.set_importer('repo-1', 'mock-importer', importer_config)

        # Test
        sync_config_override = {'clint' : 'hawkeye'}
        self.sync_manager.sync('repo-1', sync_config_override=sync_config_override)

        # Verify
        repo = Repo.get_collection().find_one({'id' : 'repo-1'})
        repo_importer = RepoImporter.get_collection().find_one({'repo_id' : 'repo-1', 'id' : 'mock-importer'})

        #   Database
        self.assertTrue(repo_importer['last_sync'] is not None)
        self.assertTrue(assert_last_sync_time(repo_importer['last_sync']))

        #   Call into the importer
        sync_args = mock_plugins.MOCK_IMPORTER.sync_repo.call_args[0]

        self.assertEqual(repo['id'], sync_args[0].id)
        self.assertTrue(sync_args[1] is not None)
        self.assertEqual({}, sync_args[2].plugin_config)
        self.assertEqual(importer_config, sync_args[2].repo_plugin_config)
        self.assertEqual(sync_config_override, sync_args[2].override_config)

    def test_sync_missing_repo(self):
        """
        Tests the proper error is raised when a non-existent repo is specified.
        """

        # Test
        try:
            self.sync_manager.sync('fake-repo')
        except repo_sync_manager.MissingResource, e:
            self.assertTrue('fake-repo' == e.resources['resource_id'])

    def test_sync_no_importer_set(self):
        """
        Tests the proper error is raised when no importer is set for the repo.
        """

        # Setup
        self.repo_manager.create_repo('importer-less') # don't set importer

        # Test
        self.assertRaises(repo_sync_manager.PulpExecutionException, self.sync_manager.sync,
                          'importer-less')

    def test_sync_bad_importer(self):
        """
        Tests the proper error is raised when an importer is set on the repo but
        the importer is no longer present as a plugin. This situation simulates
        a case where a repo was once successfully configured but the server
        has since been bounced and the importer plugin removed.
        """

        # Setup
        self.repo_manager.create_repo('old-repo')
        self.importer_manager.set_importer('old-repo', 'mock-importer', None)

        #   Simulate bouncing the server and removing the importer plugin
        mock_plugins.IMPORTER_MAPPINGS.pop('mock-importer')

        # Test
        try:
            self.sync_manager.sync('old-repo')
            self.fail('An Exception should have been raised.')
        except repo_sync_manager.MissingResource, e:
            self.assertTrue('old-repo' == e.resources['resource_id'])

    def test_sync_bad_database(self):
        """
        Tests the case where the database got itself in a bad state where the
        repo thinks it has an importer but the importer-repo relationship doc
        doesn't exist in the database.
        """

        # Setup
        self.repo_manager.create_repo('good-repo')
        self.importer_manager.set_importer('good-repo', 'mock-importer', None)

        RepoImporter.get_collection().remove()

        self.assertRaises(repo_sync_manager.PulpExecutionException, self.sync_manager.sync,
                          'good-repo')

    def test_sync_with_error(self):
        """
        Tests a sync when the plugin raises an error.
        """

        # Setup
        class FakePluginException(Exception): pass

        error_msg = 'Error test'
        mock_plugins.MOCK_IMPORTER.sync_repo.side_effect = FakePluginException(error_msg)

        self.repo_manager.create_repo('gonna-bail')
        self.importer_manager.set_importer('gonna-bail', 'mock-importer', {})

        # Test
        self.assertRaises(Exception, self.sync_manager.sync, 'gonna-bail')

        # Verify

        # Database
        repo_importer = RepoImporter.get_collection().find_one({'repo_id' : 'gonna-bail', 'id' : 'mock-importer'})

        self.assertTrue(repo_importer['last_sync'] is not None)
        self.assertTrue(assert_last_sync_time(repo_importer['last_sync']))

        #    History Entry
        history = list(RepoSyncResult.get_collection().find({'repo_id' : 'gonna-bail'}))
        self.assertEqual(1, len(history))
        self.assertEqual('gonna-bail', history[0]['repo_id'])
        self.assertEqual(RepoSyncResult.RESULT_ERROR, history[0]['result'])
        self.assertEqual('mock-importer', history[0]['importer_id'])
        self.assertEqual('mock-importer', history[0]['importer_type_id'])
        self.assertTrue(history[0]['started'] is not None)
        self.assertTrue(history[0]['completed'] is not None)

        self.assertTrue(history[0]['added_count'] is None)
        self.assertTrue(history[0]['updated_count'] is None)
        self.assertTrue(history[0]['removed_count'] is None)
        self.assertTrue(history[0]['summary'] is None)
        self.assertTrue(history[0]['details'] is None)

        self.assertEqual(error_msg, history[0]['error_message'])
        self.assertTrue('FakePluginException' in history[0]['exception'])
        self.assertTrue(history[0]['traceback'] is not None)

        # Cleanup
        mock_plugins.MOCK_IMPORTER.sync_repo.side_effect = None

    def _test_sync_with_auto_publish(self):
        """
        Tests that the autodistribute call is properly called at the tail end
        of a successful sync.
        """

        # Setup
        manager_factory.register_manager(manager_factory.TYPE_REPO_PUBLISH, MockRepoPublishManager)

        self.repo_manager.create_repo('repo')
        self.importer_manager.set_importer('repo', 'mock-importer', {})

        # Test
        self.sync_manager.sync('repo')

        # Verify
        self.assertEqual('repo', MockRepoPublishManager.repo_id)
        self.assertEqual({}, MockRepoPublishManager.base_progress_report)

    def _test_sync_with_auto_publish_error(self):
        """
        Tests that the autodistribute exception is propagated when one or more auto publish calls fail.
        """

        # Setup
        manager_factory.register_manager(manager_factory.TYPE_REPO_PUBLISH, MockRepoPublishManager)
        MockRepoPublishManager.raise_error = True

        self.repo_manager.create_repo('doa')
        self.importer_manager.set_importer('doa', 'mock-importer', {})

        # Test
        try:
            self.sync_manager.sync('doa')
            self.fail('Expected exception not thrown')
        except repo_publish_manager.PulpExecutionException, e:
            #self.assertTrue('doa' in e)
            pass

    def test_sync_no_plugin_report(self):
        """
        Tests synchronizing against a sloppy plugin that doesn't return a sync report.
        """

        # Setup
        self.repo_manager.create_repo('repo-1')
        self.importer_manager.set_importer('repo-1', 'mock-importer', {})

        mock_plugins.MOCK_IMPORTER.sync_repo.return_value = None # sloppy plugin

        # Test
        self.sync_manager.sync('repo-1')

        # Verify

        #   History Entry
        history = list(RepoSyncResult.get_collection().find({'repo_id' : 'repo-1'}))
        self.assertEqual(1, len(history))
        self.assertEqual('repo-1', history[0]['repo_id'])
        self.assertEqual(RepoSyncResult.RESULT_ERROR, history[0]['result'])
        self.assertEqual('mock-importer', history[0]['importer_id'])
        self.assertEqual('mock-importer', history[0]['importer_type_id'])
        self.assertTrue(history[0]['started'] is not None)
        self.assertTrue(history[0]['completed'] is not None)

        self.assertEqual(-1, history[0]['added_count'])
        self.assertEqual(-1, history[0]['updated_count'])
        self.assertEqual(-1, history[0]['removed_count'])

        expected_message = ('Plugin type [mock-importer] on repo [repo-1] did not return a valid '
                            'sync report')
        self.assertEqual(expected_message, history[0]['summary'])
        self.assertEqual(expected_message, history[0]['details'])

        self.assertTrue(history[0]['error_message'] is None)
        self.assertTrue(history[0]['exception'] is None)
        self.assertTrue(history[0]['traceback'] is None)

    def test_sync_history(self):
        """
        Tests retrieving sync history for a repo.
        """

        # Setup
        self.repo_manager.create_repo('creeper')
        for i in range(1, 10):
            add_result('creeper', i)

        # Test
        entries = self.sync_manager.sync_history('creeper')

        # Verify there are 9 entries and they are in descending order
        self.assertEqual(9, len(entries))
        for entry in entries:
            first = dateutils.parse_iso8601_datetime(entry['started'])
            second = dateutils.parse_iso8601_datetime(entry['started'])
            self.assertTrue(first >= second)

    def test_sync_history_with_limit(self):
        """
        Tests retrieving only a subset of all history entries
        """

        # Setup
        self.repo_manager.create_repo('zombie')
        for i in range(1, 10):
            add_result('zombie', i)

        # Test with a valid limit
        entries = self.sync_manager.sync_history('zombie', limit=3)
        self.assertEqual(3, len(entries))
        # Verify descending order.
        for entry in entries:
            first = dateutils.parse_iso8601_datetime(entry['started'])
            second = dateutils.parse_iso8601_datetime(entry['started'])
            self.assertTrue(first >= second)

    def test_sync_history_invalid_limit(self):
        """
        Tests that limit is checked for invalid values
        """

        # Setup
        self.repo_manager.create_repo('test_repo')
        for i in range(1, 5):
            add_result('test_repo', i)

        # Try an invalid limit
        self.assertRaises(InvalidValue, self.sync_manager.sync_history, 'test_repo', limit=0)
        # Try a non-int value
        self.assertRaises(InvalidValue, self.sync_manager.sync_history, 'test_repo', limit='string')

    def test_sync_history_ascending_sort(self):
        """
        Tests the sort functionality of sync_history
        """

        # Setup
        self.repo_manager.create_repo('test_sort')
        date_string = '2013-06-01T12:00:0%sZ'
        # Add some consecutive sync entries
        for i in range(0, 10, 2):
            r = RepoSyncResult.expected_result('test_sort', 'foo', 'bar', date_string % str(i),
                                               date_string % str(i + 1), 1, 1, 1, '', '',
                                               RepoSyncResult.RESULT_SUCCESS)
            RepoSyncResult.get_collection().save(r, safe=True)

        # Test sort by ascending start date
        entries = self.sync_manager.sync_history(repo_id='test_sort', sort=constants.SORT_ASCENDING)
        self.assertEqual(5, len(entries))
        # Verify that each entry has a earlier completed date than the next one
        for i in range(0, 4):
            first = dateutils.parse_iso8601_datetime(entries[i]['started'])
            second = dateutils.parse_iso8601_datetime(entries[i + 1]['started'])
            self.assertTrue(first < second)

    def test_sync_history_descending_sort(self):

        # Setup
        self.repo_manager.create_repo('test_sort')
        date_string = '2013-06-01T12:00:0%sZ'
        # Add some consecutive sync entries
        for i in range(0, 10, 2):
            r = RepoSyncResult.expected_result('test_sort', 'foo', 'bar', date_string % str(i),
                                               date_string % str(i + 1), 1, 1, 1, '', '',
                                               RepoSyncResult.RESULT_SUCCESS)
            RepoSyncResult.get_collection().save(r, safe=True)

        # Test sort by descending start date
        entries = self.sync_manager.sync_history(repo_id='test_sort', sort=constants.SORT_DESCENDING)
        self.assertEqual(5, len(entries))
        # Verify that each entry has a later completed date than the next one
        for i in range(0, 4):
            first = dateutils.parse_iso8601_datetime(entries[i]['started'])
            second = dateutils.parse_iso8601_datetime(entries[i + 1]['started'])
            self.assertTrue(first > second)

    def test_sync_history_invalid_sort(self):

        # Setup
        self.repo_manager.create_repo('test_sort')
        for i in range(1, 5):
            add_result('test_sort', i)

        # Verify an InvalidValue exception is raised if an incorrect sort option is given
        self.assertRaises(InvalidValue, self.sync_manager.sync_history, repo_id='test_sort', sort='rand')

    def test_sync_history_start_date(self):
        """
        Tests the functionality of requesting sync history after a given date
        """

        # Setup
        self.repo_manager.create_repo('test_repo')
        # A date string to fake some dates
        date_string = '2013-06-01T12:00:0%sZ'
        # Create 3 entries, with each date entry one second later
        for i in range(0, 6, 2):
            r = RepoSyncResult.expected_result('test_repo', 'foo', 'bar', date_string % str(i),
                                               date_string % str(i + 1), 1, 1, 1, '', '',
                                               RepoSyncResult.RESULT_SUCCESS)
            RepoSyncResult.get_collection().save(r, safe=True)

        # Verify three entries in test_repo
        self.assertEqual(3, len(self.sync_manager.sync_history('test_repo')))
        # Retrieve the last two entries
        start_date = '2013-06-01T12:00:02Z'
        start_entries = self.sync_manager.sync_history('test_repo', start_date=start_date)

        # Verify all entries have dates greater than or equal to the given start date
        self.assertEqual(2, len(start_entries))
        for entries in start_entries:
            retrieved = dateutils.parse_iso8601_datetime(entries['started'])
            given_start = dateutils.parse_iso8601_datetime(start_date)
            self.assertTrue(retrieved >= given_start)

    def test_sync_history_end_date(self):
        """
        Tests the functionality of requesting sync history before a given date
        """
        # Setup
        self.repo_manager.create_repo('test_repo')
        # A date string to fake some dates
        date_string = '2013-06-01T12:00:0%sZ'
        # Create 3 entries, with each date entry one second later
        for i in range(0, 6, 2):
            r = RepoSyncResult.expected_result('test_repo', 'foo', 'bar', date_string % str(i),
                                               date_string % str(i + 1), 1, 1, 1, '', '',
                                               RepoSyncResult.RESULT_SUCCESS)
            RepoSyncResult.get_collection().save(r, safe=True)

        # Verify three entries in test_repo
        self.assertEqual(3, len(self.sync_manager.sync_history('test_repo')))
        # Retrieve the first two entries
        end_date = '2013-06-01T12:00:03Z'
        end_entries = self.sync_manager.sync_history('test_repo', end_date=end_date)
        # Confirm the dates of the retrieved entries are earlier than or equal to the requested date
        self.assertEqual(2, len(end_entries))
        for entry in end_entries:
            retrieved = dateutils.parse_iso8601_datetime(entry['started'])
            given_end = dateutils.parse_iso8601_datetime(end_date)
            self.assertTrue(retrieved <= given_end)

    def test_sync_history_invalid_date(self):

        # Setup
        self.repo_manager.create_repo('test_repo')
        for i in range(1, 5):
            add_result('test_repo', i)

        # Verify an InvalidValue exception is raised with malformed dates
        self.assertRaises(InvalidValue, self.sync_manager.sync_history, 'test_repo',
                          start_date='2013-56-01T12:00:02')
        self.assertRaises(InvalidValue, self.sync_manager.sync_history, 'test_repo',
                          end_date='2013-56-01T12:00:02')

    def test_sync_history_missing_repo(self):
        """
        Tests getting sync history for a repo that doesn't exist.
        """

        # Test
        try:
            self.sync_manager.sync_history('endermen')
            self.fail('Exception expected')
        except repo_sync_manager.MissingResource, e:
            self.assertTrue('endermen' == e.resources['resource_id'])

    def test_get_repo_storage_directory(self):
        """
        Tests a repo storage directory can be retrieved and is created in the process.
        """

        # Setup
        temp_dir = '/tmp/test-repo-storage-dir'

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        repo_sync_manager.REPO_STORAGE_DIR = temp_dir

        # Test
        dir = self.sync_manager.get_repo_storage_directory('test-repo')

        # Verify
        self.assertEqual(dir, temp_dir + '/test-repo')
        self.assertTrue(os.path.exists(dir))


class TestDoSync(base.PulpServerTests):
    """
    Assert correct behavior from the _do_sync() method.
    """
    def setUp(self):
        super(TestDoSync, self).setUp()
        mock_plugins.install()
        self.repo_manager = repo_manager.RepoManager()
        self.importer_manager = repo_importer_manager.RepoImporterManager()
        self.sync_manager = repo_sync_manager.RepoSyncManager()

    def tearDown(self):
        super(TestDoSync, self).tearDown()
        mock_plugins.reset()
        manager_factory.reset()
        Repo.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoSyncResult.get_collection().remove()
        MockRepoPublishManager.reset()

    @mock.patch('pulp.server.managers.repo.sync.register_sigterm_handler',
                side_effect=tasks.register_sigterm_handler)
    def test_wraps_publish_in_register_sigterm_handler(self, register_sigterm_handler):
        """
        Assert that the importer's sync_repo() method gets wrapped by the register_sigterm_handler
        decorator before it is run.
        """
        def sync_repo(self, *args, **kwargs):
            """ 
            This method will be attached to the importer_instance, and will allow us to assert
            that the register_sigterm_handler is called before the sync_repo is called. We can tell
            because inside here the SIGTERM handler has been altered.
            """
            signal_handler = signal.getsignal(signal.SIGTERM)
            self.assertNotEqual(signal_handler, starting_term_handler)

            # Make sure that the signal handler is the importer's cancel method
            self.assertEqual(importer_instance.cancel_sync_repo.call_count, 0)
            signal_handler(signal.SIGTERM, None)
            self.assertEqual(importer_instance.cancel_sync_repo.call_count, 1)

        sync_config = {'foo' : 'bar'}
        importer_id = 'dist-1'
        repo_id = 'repo-1'
        repo = self.repo_manager.create_repo(repo_id)
        self.importer_manager.set_importer(repo_id, 'mock-importer', sync_config)
        importer_instance, importer_config = \
            repo_sync_manager.RepoSyncManager._get_importer_instance_and_config(repo_id)
        # Set our special sync_repo() from above to the instance so we can make our assertions
        importer_instance.sync_repo = sync_repo
        transfer_repo = mock.MagicMock()
        conduit = mock.MagicMock()
        call_config = mock.MagicMock()
        starting_term_handler = signal.getsignal(signal.SIGTERM)

        repo_sync_manager.RepoSyncManager._do_sync(repo, importer_instance,
                                                   transfer_repo, conduit, call_config)

        register_sigterm_handler.assert_called_once_with(sync_repo,
                                                importer_instance.cancel_sync_repo)
        # Make sure the TERM handler is set back to normal
        self.assertEqual(signal.getsignal(signal.SIGTERM), starting_term_handler)


def assert_last_sync_time(time_in_iso):
    now = dateutils.now_utc_datetime_with_tzinfo()
    finished = dateutils.parse_iso8601_datetime(time_in_iso)

    # Compare them within a threshold since they won't be exact
    difference = now - finished
    return difference.seconds < 2


def add_result(repo_id, offset):
    started = dateutils.now_utc_datetime_with_tzinfo()
    completed = started + datetime.timedelta(days=offset)
    r = RepoSyncResult.expected_result(
        repo_id, 'foo', 'bar', dateutils.format_iso8601_datetime(started),
        dateutils.format_iso8601_datetime(completed), 1, 1, 1, '', '',
        RepoSyncResult.RESULT_SUCCESS)
    RepoSyncResult.get_collection().save(r, safe=True)
