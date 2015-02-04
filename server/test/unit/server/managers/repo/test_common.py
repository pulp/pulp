import datetime
import unittest

import mock

from pulp.common import dateutils
from pulp.server.managers.repo._common import to_transfer_repo, _ensure_tz_specified,\
    get_working_directory, delete_working_directory, create_worker_working_directory,\
    delete_worker_working_directory


class TestToTransferRepo(unittest.TestCase):

    def test_to_transfer_repo(self):

        dt = dateutils.now_utc_datetime_with_tzinfo()
        data = {
            'id': 'foo',
            'display_name': 'bar',
            'description': 'baz',
            'notes': 'qux',
            'content_unit_counts': {'units': 1},
            'last_unit_added': dt,
            'last_unit_removed': dt
        }

        repo = to_transfer_repo(data)
        self.assertEquals('foo', repo.id)
        self.assertEquals('bar', repo.display_name)
        self.assertEquals('baz', repo.description)
        self.assertEquals('qux', repo.notes)
        self.assertEquals({'units': 1}, repo.content_unit_counts)
        self.assertEquals(dt, repo.last_unit_added)
        self.assertEquals(dt, repo.last_unit_removed)

    def test_to_transfer_repo_unit_timestamps_not_specified(self):
        data = {
            'id': 'foo',
            'display_name': 'bar',
            'description': 'baz',
            'notes': 'qux',
            'content_unit_counts': {'units': 1}
        }

        repo = to_transfer_repo(data)
        self.assertEquals(None, repo.last_unit_added)
        self.assertEquals(None, repo.last_unit_removed)


class TestEnsureTzSpecified(unittest.TestCase):

    def test_tz_not_specified(self):
        dt = datetime.datetime.utcnow()
        new_date = _ensure_tz_specified(dt)
        self.assertEquals(new_date.tzinfo, dateutils.utc_tz())

    def test_none_object(self):
        dt = None
        new_date = _ensure_tz_specified(dt)
        self.assertEquals(new_date, None)

    def test_tz_specified(self):
        dt = datetime.datetime.now(dateutils.local_tz())
        new_date = _ensure_tz_specified(dt)
        self.assertEquals(new_date.tzinfo, dateutils.utc_tz())


class TestWorkingDirectory(unittest.TestCase):

    @mock.patch('os.mkdir')
    @mock.patch('pulp.server.config.config.get')
    def test_create_worker_working_directory(self, mock_pulp_config_get, mock_mkdir):
        mock_pulp_config_get.return_value = '/var/cache/pulp'
        create_worker_working_directory('test-worker')
        mock_pulp_config_get.assert_called_with('server', 'working_directory')
        mock_mkdir.assert_called_with('/var/cache/pulp/test-worker')

    @mock.patch('shutil.rmtree')
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('pulp.server.config.config.get')
    def test_delete_worker_working_directory(self, mock_pulp_config_get, mock_path_exists,
                                             mock_rmtree):
        mock_pulp_config_get.return_value = '/var/cache/pulp'
        delete_worker_working_directory('test-worker')
        mock_pulp_config_get.assert_called_with('server', 'working_directory')
        mock_path_exists.assert_called_with('/var/cache/pulp/test-worker')
        mock_rmtree.assert_called_with('/var/cache/pulp/test-worker')

    @mock.patch('celery.task.current')
    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('os.mkdir')
    @mock.patch('pulp.server.config.config.get')
    def test_get_working_directory_new(self, mock_pulp_config_get, mock_mkdir, mock_path_exists,
                                       mock_celery_current_task):
        mock_pulp_config_get.return_value = '/var/cache/pulp'
        mock_celery_current_task.request = mock.Mock(id='mock-task-id', hostname='mock-host')
        working_directory_path = get_working_directory()
        mock_pulp_config_get.assert_called_with('server', 'working_directory')
        mock_mkdir.assert_called_with('/var/cache/pulp/mock-host/mock-task-id')
        self.assertEqual(working_directory_path, '/var/cache/pulp/mock-host/mock-task-id')

    @mock.patch('celery.task.current')
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.mkdir')
    @mock.patch('pulp.server.config.config.get')
    def test_get_working_directory_existing(self, mock_pulp_config_get, mock_mkdir,
                                            mock_path_exists, mock_celery_current_task):
        mock_pulp_config_get.return_value = '/var/cache/pulp'
        mock_celery_current_task.request = mock.Mock(id='mock-task-id', hostname='mock-host')
        working_directory_path = get_working_directory()
        mock_pulp_config_get.assert_called_with('server', 'working_directory')
        self.assertFalse(mock_mkdir.called, 'os.mkdir should not have been called')
        self.assertEqual(working_directory_path, '/var/cache/pulp/mock-host/mock-task-id')

    @mock.patch('celery.task.current')
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('shutil.rmtree')
    @mock.patch('pulp.server.config.config.get')
    def test_delete_working_directory_existing(self, mock_pulp_config_get, mock_rmtree,
                                               mock_path_exists, mock_celery_current_task):
        mock_pulp_config_get.return_value = '/var/cache/pulp'
        mock_celery_current_task.request = mock.Mock(id='mock-task-id', hostname='mock-host')
        delete_working_directory()
        mock_pulp_config_get.assert_called_with('server', 'working_directory')
        mock_rmtree.assert_called_with('/var/cache/pulp/mock-host/mock-task-id')

    @mock.patch('celery.task.current')
    @mock.patch('os.path.exists', return_value=False)
    @mock.patch('shutil.rmtree')
    @mock.patch('pulp.server.config.config.get')
    def test_delete_working_directory_non_existing(self, mock_pulp_config_get, mock_rmtree,
                                                   mock_path_exists, mock_celery_current_task):
        mock_pulp_config_get.return_value = '/var/cache/pulp'
        mock_celery_current_task.request = mock.Mock(id='mock-task-id', hostname='mock-host')
        delete_working_directory()
        mock_pulp_config_get.assert_called_with('server', 'working_directory')
        self.assertFalse(mock_rmtree.called, "Nothing should be removed.")
