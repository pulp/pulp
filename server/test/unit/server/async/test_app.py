"""
This module contains tests for the pulp.server.async.app module.
"""

import platform
import signal
import unittest

from django.db.utils import IntegrityError

import mock

from pulp.server.managers.factory import initialize
from pulp.tasking import celery_app as app
from pulp.tasking.constants import TASKING_CONSTANTS, 

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
        sender = TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME + '@' + platform.node()
        # The instance argument isn't used and don't matter, so we'll just pass a mock
        app.initialize_worker(sender, mock.MagicMock())

        initialize.assert_called_once_with()
        delete_worker.assert_called_once_with(sender, normal_shutdown=True)
        create_worker_working_directory.assert_called_once_with(sender)
        delete_worker_working_directory.assert_called_once_with(sender)
        mock_get_resource_manager_lock.assert_called_once_with(sender)

    @mock.patch('pulp.tasking.celery_app.time')
    @mock.patch('pulp.app.models.task.Worker')
    @mock.patch('pulp.app.models.task.TaskLock')
    def test_get_resource_manager_lock(self, mock_lock, mock_worker, mock_time):
        """
        Assert that get_resource_manager_lock() attempts to save a lock to the database with the
        correct name, and that it creates a worker entry with that name and the correct timestamp,
        and that a failure to save the lock will cause it to sleep and retry acquisition.
        """
        sender = TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME + '@' + platform.node()
        mock_lock().save.side_effect = [IntegrityError, None]
        app.get_resource_manager_lock(sender)
        mock_worker_inst = mock.MagickMock()
        mock_worker.objects.get_or_create.return_value = (mock_worker_inst, True)

        mock_worker.objects.get_or_create.assert_called_once_with(name=sender)
        self.assertEquals(2, mock_worker_inst.heartbeat.call_count)

        self.assertEquals(2, mock_lock().save.call_count)
        mock_time.sleep.assert_called_once_with(TASKING_CONSTANTS.CELERY_CHECK_INTERVAL)

    @mock.patch('pulp.server.async.app.sys')
    @mock.patch('pulp.server.async.app.tasks.delete_worker')
    def test_custom_sigterm_handler(self, delete_worker, mock_sys):
        """
        Assert that the signal handler installed by the custom_sigterm_handler context manager
        calls the delete_worker cleanup routine with the correct worker name and then exits.
        """
        name = TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME + '@' + platform.node()

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

        name = TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME + '@' + platform.node()

        with app.custom_sigterm_handler(name):
            handler = signal.getsignal(signal.SIGTERM)
            handler(None, None)

        handler = signal.getsignal(signal.SIGTERM)
        self.assertEquals(handler, signal.SIG_DFL)
