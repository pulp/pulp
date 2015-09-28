"""
This module contains tests for the pulp.server.async.app module.
"""
import unittest

import mock

from pulp.server.async import app


class InitializeWorkerTestCase(unittest.TestCase):
    """
    This class contains tests for the initialize_worker() function.
    """
    @mock.patch('pulp.server.async.app.common_utils.delete_worker_working_directory')
    @mock.patch('pulp.server.async.app.common_utils.create_worker_working_directory')
    @mock.patch('pulp.server.async.app.initialization.initialize')
    @mock.patch('pulp.server.async.app.tasks._delete_worker')
    def test_initialize_worker(self, _delete_worker, initialize, create_worker_working_directory,
                               delete_worker_working_directory):
        """
        Assert that initialize_worker() calls Pulp's initialization code and the appropriate worker
        monitoring code.
        """
        sender = mock.MagicMock()
        # The args aren't used and don't matter, so we'll just pass some mocks
        app.initialize_worker(sender, mock.MagicMock())

        initialize.assert_called_once_with()
        _delete_worker.assert_called_once_with(sender, normal_shutdown=True)
        create_worker_working_directory.assert_called_once_with(sender)
        delete_worker_working_directory.assert_called_once_with(sender)
