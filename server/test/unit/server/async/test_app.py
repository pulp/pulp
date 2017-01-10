"""
This module contains tests for the pulp.server.async.app module.
"""

import mongoengine
import platform
import unittest

import mock

from pulp.common.constants import RESOURCE_MANAGER_WORKER_NAME, PULP_PROCESS_HEARTBEAT_INTERVAL
from pulp.server.async import app
from pulp.server.managers.factory import initialize


initialize()


class InitializeWorkerTestCase(unittest.TestCase):
    """
    This class contains tests for the initialize_worker() function.
    """
    @mock.patch('pulp.server.async.app.common_utils.delete_worker_working_directory')
    @mock.patch('pulp.server.async.app.common_utils.create_worker_working_directory')
    @mock.patch('pulp.server.async.app.initialization.initialize')
    @mock.patch('pulp.server.async.app.tasks._delete_worker')
    @mock.patch('pulp.server.async.app.get_resource_manager_lock')
    def test_initialize_worker(self,
                               mock_get_resource_manager_lock,
                               _delete_worker, initialize,
                               create_worker_working_directory,
                               delete_worker_working_directory):
        """
        Assert that initialize_worker() calls Pulp's initialization code and the appropriate worker
        monitoring code for a non-resource mananger worker.
        """
        sender = 'reserved_resource_worker-0' + '@' + platform.node()
        # The instance argument isn't used and don't matter, so we'll just pass a mock
        app.initialize_worker(sender, mock.MagicMock())

        initialize.assert_called_once_with()
        _delete_worker.assert_called_once_with(sender, normal_shutdown=True)
        create_worker_working_directory.assert_called_once_with(sender)
        delete_worker_working_directory.assert_called_once_with(sender)
        mock_get_resource_manager_lock.assert_not_called()

    @mock.patch('pulp.server.async.app.common_utils.delete_worker_working_directory')
    @mock.patch('pulp.server.async.app.common_utils.create_worker_working_directory')
    @mock.patch('pulp.server.async.app.initialization.initialize')
    @mock.patch('pulp.server.async.app.tasks._delete_worker')
    @mock.patch('pulp.server.async.app.get_resource_manager_lock')
    def test_initialize_worker_resource_manager(self,
                                                mock_get_resource_manager_lock,
                                                _delete_worker, initialize,
                                                create_worker_working_directory,
                                                delete_worker_working_directory):
        """
        Assert that initialize_worker() calls Pulp's initialization code and the appropriate worker
        monitoring code for a resource mananger worker.
        """
        sender = RESOURCE_MANAGER_WORKER_NAME + '@' + platform.node()
        # The instance argument isn't used and don't matter, so we'll just pass a mock
        app.initialize_worker(sender, mock.MagicMock())

        initialize.assert_called_once_with()
        _delete_worker.assert_called_once_with(sender, normal_shutdown=True)
        create_worker_working_directory.assert_called_once_with(sender)
        delete_worker_working_directory.assert_called_once_with(sender)
        mock_get_resource_manager_lock.assert_called_once_with(sender)

    @mock.patch('pulp.server.async.app.time')
    @mock.patch('pulp.server.async.app.datetime')
    @mock.patch('pulp.server.async.app.Worker')
    @mock.patch('pulp.server.async.app.ResourceManagerLock')
    def test_get_resource_manager_lock(self, mock_rm_lock, mock_worker, mock_datetime, mock_time):
        """
        Assert that get_resource_manager_lock() attempts to save a lock to the database with the
        correct name, and that it creates a worker entry with that name and the correct timestamp,
        and that a failure to save the lock will cause it to sleep and retry acquisition.
        """
        sender = RESOURCE_MANAGER_WORKER_NAME + '@' + platform.node()
        mock_rm_lock().save.side_effect = [mongoengine.NotUniqueError(), None]
        app.get_resource_manager_lock(sender)

        mock_worker.objects(name=sender).update_one.\
            assert_called_with(set__last_heartbeat=mock_datetime.utcnow(), upsert=True)

        self.assertEquals(2, len(mock_rm_lock().save.mock_calls))
        mock_time.sleep.assert_called_once_with(PULP_PROCESS_HEARTBEAT_INTERVAL)
