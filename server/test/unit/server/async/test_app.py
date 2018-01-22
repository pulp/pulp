"""
This module contains tests for the pulp.server.async.app module.
"""

import mongoengine
import platform
import unittest

import mock

from pulp.common.constants import RESOURCE_MANAGER_WORKER_NAME
from pulp.server.async import app
from pulp.server.constants import PULP_PROCESS_HEARTBEAT_INTERVAL
from pulp.server.managers.factory import initialize


initialize()


class InitializeWorkerTestCase(unittest.TestCase):

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
