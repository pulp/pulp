import unittest

import mock

from pulp.bindings.server import PulpConnection
from pulp.bindings.static import StaticRequest


class TestStaticRequest(unittest.TestCase):
    """
    Tests for static file requests.
    """

    def test_get_server_key(self):
        """
        Test that the correct path is given to the binding.
        """
        static_request = StaticRequest(mock.MagicMock(spec=PulpConnection))
        response = static_request.get_server_key()
        static_request.server.GET.assert_called_once_with('/pulp/static/rsa_pub.key',
                                                          ignore_prefix=True)
        self.assertTrue(response is static_request.server.GET.return_value)
