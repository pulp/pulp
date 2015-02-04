import mock
import unittest

import pulp.repoauth.auth_handler_framework as auth_framework


# Functions that simulate plugins so we can influence the outcome
def fail(request):
    return False


def win(request):
    return True


class MockFunctionsTests(unittest.TestCase):
    def test_handle_fail_required_pass_optional(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = [win, win, fail]
        auth_framework.OPTIONAL_PLUGINS = [win]

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.HTTP_UNAUTHORIZED, http_code)

    def test_handle_pass_required_fail_optional(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = [win, win]
        auth_framework.OPTIONAL_PLUGINS = [fail, fail, fail]

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.HTTP_UNAUTHORIZED, http_code)

    def test_handle_pass_required_pass_optional(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = [win, win]
        auth_framework.OPTIONAL_PLUGINS = [fail, fail, win]

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.OK, http_code)

    def test_handle_pass_no_optional(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = [win]
        auth_framework.OPTIONAL_PLUGINS = []

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.OK, http_code)

    def test_handle_fail_no_optional(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = [fail]
        auth_framework.OPTIONAL_PLUGINS = []

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.HTTP_UNAUTHORIZED, http_code)

    def test_handle_no_plugins(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = []
        auth_framework.OPTIONAL_PLUGINS = []

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.OK, http_code)


class TestAuthenhandler(unittest.TestCase):

    @mock.patch("pulp.repoauth.auth_handler_framework._handle")
    def test_authenhandler(self, mock_handle):
        mock_handle.return_value = "some_value"
        request = MockRequest()

        result = auth_framework.authenhandler(request)

        self.assertEqual(result, "some_value")
        self.assertEqual(request.user, "some-user")

    @mock.patch("pulp.repoauth.auth_handler_framework._handle")
    def test_authenhandler_ok(self, mock_handle):
        mock_handle.return_value = auth_framework.apache.OK
        request = MockRequest()

        auth_framework.authenhandler(request)

        self.assertEqual(request.user, "pulp_user")


class MockRequest(object):

    def __init__(self):
        self.user = "some-user"

    def add_common_vars(self):
        pass

    def log_error(self, message):
        pass
