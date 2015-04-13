import unittest
import mock

from pulp.repoauth.wsgi import allow_access


class TestWsgi(unittest.TestCase):

    def setUp(self):
        """
        set up authenticators
        """
        # build authenticators w/ entry points
        self.mock_auth_one = mock.Mock()
        mock_ep_one = mock.Mock()
        mock_ep_one.name = 'auth_one'
        mock_ep_one.load.return_value = self.mock_auth_one

        self.mock_auth_two = mock.Mock()
        mock_ep_two = mock.Mock()
        mock_ep_two.name = 'auth_two'
        mock_ep_two.load.return_value = self.mock_auth_two

        self.mock_ep_list = [mock_ep_one, mock_ep_two]

    @mock.patch('pulp.repoauth.auth_enabled_validation.authenticate')
    def test_auth_disabled(self, mock_auth_enabled):
        """
        Test that we can disable auth via config flag
        """
        # NB: 'True' means that auth is disabled
        mock_auth_enabled.return_value = True
        mock_environ = mock.Mock()

        self.assertTrue(allow_access(mock_environ, 'fake.host.name'))

    @mock.patch('pulp.repoauth.wsgi.iter_entry_points')
    def test_check_entry_points(self, mock_iter_ep):
        """
        Test that entry points are loaded
        """
        mock_environ = mock.Mock()
        mock_iter_ep.return_value = self.mock_ep_list

        self.assertTrue(allow_access(mock_environ, 'fake.host.name'))
        self.mock_auth_one.assert_called_once_with(mock_environ)
        self.mock_auth_two.assert_called_once_with(mock_environ)

    @mock.patch('pulp.repoauth.wsgi.iter_entry_points')
    def test_deny_one(self, mock_iter_ep):
        """
        Test for when one auth fails but not the other
        """
        mock_environ = mock.Mock()

        self.mock_auth_one.return_value = True
        self.mock_auth_two.return_value = False
        mock_iter_ep.return_value = self.mock_ep_list

        self.assertFalse(allow_access(mock_environ, 'fake.host.name'))

    @mock.patch('pulp.repoauth.wsgi.iter_entry_points')
    def test_deny_one_stops_loop(self, mock_iter_ep):
        """
        Test that we bail out if either authenticator is False
        """
        mock_environ = mock.Mock()

        self.mock_auth_one.return_value = False
        self.mock_auth_two.return_value = False
        mock_iter_ep.return_value = self.mock_ep_list

        self.assertFalse(allow_access(mock_environ, 'fake.host.name'))
        # we don't know if auth_one or auth_two will occur first
        total_calls = self.mock_auth_one.call_count + self.mock_auth_two.call_count
        self.assertEquals(total_calls, 1)

    @mock.patch('pulp.repoauth.wsgi.iter_entry_points')
    def test_successful_auth(self, mock_iter_ep):
        """
        Test for when all auth methods succeed
        """
        mock_environ = mock.Mock()

        self.mock_auth_one.return_value = True
        self.mock_auth_two.return_value = True
        mock_iter_ep.return_value = self.mock_ep_list

        self.assertTrue(allow_access(mock_environ, 'fake.host.name'))
