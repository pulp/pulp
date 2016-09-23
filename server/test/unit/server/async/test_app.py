"""
This module contains tests for the pulp.server.async.app module.
"""

import mongoengine
import platform
import unittest
import signal

import mock

from pulp.common.constants import RESOURCE_MANAGER_WORKER_NAME, CELERY_CHECK_INTERVAL
from pulp.server.managers.factory import initialize
from pulp.tasking import celery_app as app


initialize()


class InitializeWorkerTestCase(unittest.TestCase):
    """
    This class contains tests for the initialize_worker() function.
    """
    @mock.patch('pulp.server.async.app.common_utils.delete_worker_working_directory')
    @mock.patch('pulp.server.async.app.common_utils.create_worker_working_directory')
    @mock.patch('pulp.server.async.app.initialization.initialize')
    @mock.patch('pulp.server.async.app.tasks.delete_worker')
    @mock.patch('pulp.server.async.app.get_resource_manager_lock')
    def test_initialize_worker(self,
                               mock_get_resource_manager_lock,
                               delete_worker, initialize,
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
        delete_worker.assert_called_once_with(sender, normal_shutdown=True)
        create_worker_working_directory.assert_called_once_with(sender)
        delete_worker_working_directory.assert_called_once_with(sender)
        mock_get_resource_manager_lock.assert_not_called()

    @mock.patch('pulp.server.async.app.common_utils.delete_worker_working_directory')
    @mock.patch('pulp.server.async.app.common_utils.create_worker_working_directory')
    @mock.patch('pulp.server.async.app.initialization.initialize')
    @mock.patch('pulp.server.async.app.tasks.delete_worker')
    @mock.patch('pulp.server.async.app.get_resource_manager_lock')
    def test_initialize_worker_resource_manager(self,
                                                mock_get_resource_manager_lock,
                                                delete_worker, initialize,
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
        delete_worker.assert_called_once_with(sender, normal_shutdown=True)
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
        mock_time.sleep.assert_called_once_with(CELERY_CHECK_INTERVAL)

    @mock.patch('pulp.server.async.app.sys')
    @mock.patch('pulp.server.async.app.tasks.delete_worker')
    def test_custom_sigterm_handler(self, delete_worker, mock_sys):
        """
        Assert that the signal handler installed by the custom_sigterm_handler context manager
        calls the delete_worker cleanup routine with the correct worker name and then exits.
        """
        name = RESOURCE_MANAGER_WORKER_NAME + '@' + platform.node()

        with app.custom_sigterm_handler(name):
            handler = signal.getsignal(signal.SIGTERM)
            self.assertNotEquals(handler, signal.SIG_DFL)

            handler(None, None)

            delete_worker.assert_called_once_with(name, normal_shutdown=True)
            mock_sys.exit.assert_called_once_with(0)

    @mock.patch('pulp.server.async.app.sys')
    @mock.patch('pulp.server.async.app.tasks.delete_worker')
    def test_custom_sigterm_handler_context_manager(self, delete_worker, mock_sys):
        """
        Assert that the custom_sigterm_handler context manager properly sets and restores the
        SIGTERM signal handler upon entry and exit.
        """
        handler = signal.getsignal(signal.SIGTERM)
        self.assertEquals(handler, signal.SIG_DFL)

        name = RESOURCE_MANAGER_WORKER_NAME + '@' + platform.node()

        with app.custom_sigterm_handler(name):
            handler = signal.getsignal(signal.SIGTERM)
            handler(None, None)

        handler = signal.getsignal(signal.SIGTERM)
        self.assertEquals(handler, signal.SIG_DFL)
