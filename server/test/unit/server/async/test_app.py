import unittest

from mock import patch

from pulp.server.async.app import init_app

APP_MODULE_PATH = 'pulp.server.async.app'

class TestInitApp(unittest.TestCase):

    @patch(APP_MODULE_PATH + '.initialize')
    def test_init_app_calls_initialize(self, mock_initialize):
        init_app()
        mock_initialize.assert_called_once_with()
