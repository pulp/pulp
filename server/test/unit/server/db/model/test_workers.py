"""
Tests for the pulp.server.db.model.workers module.
"""
import unittest

from pulp.server.db.model.workers import Worker


class TestWorkerModel(unittest.TestCase):
    """
    Test the Worker class
    """

    def test_queue_name(self):
        worker = Worker()
        worker.name = "fake-worker"
        self.assertEquals(worker.queue_name, 'fake-worker.dq')
