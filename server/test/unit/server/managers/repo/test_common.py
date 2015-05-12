import unittest

import mock

from pulp.server.managers.repo._common import (
    get_working_directory, delete_working_directory,
    create_worker_working_directory, delete_worker_working_directory
)


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
