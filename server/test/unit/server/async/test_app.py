"""
This module contains tests for the pulp.server.async.app module.
"""
import unittest

import mock

from pulp.server.async import app


class InitializePulpTestCase(unittest.TestCase):
    """
    This class contains tests for the initialize_pulp() function.
    """
    @mock.patch('pulp.server.async.app.initialization.initialize')
    def test_initialize_pulp(self, initialize):
        """
        Assert that initialize_pulp() calls Pulp's initialization code.
        """
        # The args aren't used and don't matter, so we'll just pass some mocks
        app.initialize_pulp(mock.MagicMock(), mock.MagicMock())

        initialize.assert_called_once_with()
