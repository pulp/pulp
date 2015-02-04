import mock
import unittest

import pulp.repoauth.auth_enabled_validation as auth_enabled_validation


class TestAuthEnabledValiation(unittest.TestCase):

    @mock.patch("pulp.repoauth.auth_enabled_validation.SafeConfigParser")
    def test_config_read(self, mock_parser):
        mock_parser_instance = mock.Mock()
        mock_parser.return_value = mock_parser_instance

        auth_enabled_validation._config()

        mock_parser_instance.read.assert_called_once_with('/etc/pulp/repo_auth.conf')

    @mock.patch("pulp.repoauth.auth_enabled_validation._config")
    def test_authenticate_enabled(self, mock_config):
        mock_config_instance = mock.Mock()
        # True for enabled, False for verbose logging
        mock_config_instance.getboolean.side_effect = [True, False]
        mock_config.return_value = mock_config_instance
        mock_environ = mock.Mock()

        result = auth_enabled_validation.authenticate(mock_environ)

        # NB: this is "False" which means Pulp will rely on the optional
        # plugins further down the chain. False means enabled:)
        self.assertEquals(result, False)

    @mock.patch("pulp.repoauth.auth_enabled_validation._config")
    def test_authenticate_disabled(self, mock_config):
        mock_config_instance = mock.Mock()
        # False for disabled, False for verbose logging
        mock_config_instance.getboolean.side_effect = [False, False]
        mock_config.return_value = mock_config_instance
        mock_environ = mock.Mock()

        result = auth_enabled_validation.authenticate(mock_environ)

        # NB: "True" means "disabled" since further checks are short-circuited.
        self.assertEquals(result, True)

    @mock.patch("pulp.repoauth.auth_enabled_validation._config")
    def test_authenticate_disabled_verbose_logging(self, mock_config):
        mock_config_instance = mock.Mock()
        # False for disabled, True for verbose logging
        mock_config_instance.getboolean.side_effect = [False, True]
        mock_config.return_value = mock_config_instance
        environ = {}
        environ["wsgi.errors"] = mock.Mock()

        auth_enabled_validation.authenticate(environ)

        logged_str = 'Repo authentication is not enabled. Skipping all checks.'
        environ["wsgi.errors"].write.assert_called_once_with(logged_str)
