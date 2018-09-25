import importlib
import os
from unittest import TestCase

from pulpcore import rqconfig


class TestRQConfig(TestCase):

    def test_env_config(self):
        """Tests that setting environment variables produces correct config for RQ."""
        os.environ['PULP_REDIS_HOST'] = 'redishost'
        os.environ['PULP_REDIS_PORT'] = '1234'
        os.environ['PULP_REDIS_PASSWORD'] = 'mypassword'
        importlib.reload(rqconfig)
        self.assertEquals(rqconfig.REDIS_HOST, 'redishost')
        self.assertEquals(rqconfig.REDIS_PORT, 1234)
        self.assertEquals(rqconfig.REDIS_PASSWORD, 'mypassword')
