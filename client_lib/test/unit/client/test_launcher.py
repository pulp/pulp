"""
This module contains tests for the pulp.client.launcher module.
"""
import os
import shutil
import stat
import tempfile
import unittest

import mock

from pulp.client import constants, launcher
from pulp.common import config


class TestCreateBindings(unittest.TestCase):
    """
    This class contains tests for the _create_bindings() function.
    """
    def setUp(self):
        self.config = config.Config()
        self.ca_path = '/some/path'
        self.config['filesystem'] = {'id_cert_dir': '/dir/', 'id_cert_filename': 'file'}
        self.config['server'] = {'host': 'awesome_host', 'port': 1234, 'verify_ssl': 'true',
                                 'ca_path': self.ca_path}

    def test_verify_ssl_false(self):
        """
        Make sure the PulpConnection is built properly when verify_ssl is False.
        """
        self.config['server']['verify_ssl'] = 'fAlsE'

        bindings = launcher._create_bindings(self.config, None, 'username', 'password')

        self.assertEqual(bindings.bindings.server.verify_ssl, False)
        self.assertEqual(bindings.bindings.server.ca_path, self.ca_path)

    def test_verify_ssl_true(self):
        """
        Make sure the PulpConnection is built properly when verify_ssl is true.
        """
        self.config['server']['verify_ssl'] = 'truE'
        # Let's also try to use a different path to make sure ca_path works right
        different_path = '/different.path'
        self.config['server']['ca_path'] = different_path

        bindings = launcher._create_bindings(self.config, None, 'username', 'password')

        self.assertEqual(bindings.bindings.server.verify_ssl, True)
        self.assertEqual(bindings.bindings.server.ca_path, different_path)


class TestEnsureUserPulpDir(unittest.TestCase):
    def setUp(self):
        self.workingdir = tempfile.mkdtemp()
        self.pulppath = os.path.join(self.workingdir, '.pulp')

    def tearDown(self):
        shutil.rmtree(self.workingdir)

    @mock.patch('os.path.expanduser')
    def test_asks_for_correct_dir(self, mock_expanduser):
        mock_expanduser.return_value = self.pulppath

        launcher.ensure_user_pulp_dir()

        mock_expanduser.assert_called_once_with(constants.USER_CONFIG_DIR)

    @mock.patch('os.path.expanduser')
    def test_does_not_exist(self, mock_expanduser):
        mock_expanduser.return_value = self.pulppath

        launcher.ensure_user_pulp_dir()

        stats = os.stat(os.path.join(self.workingdir, '.pulp'))
        actual_mode = stat.S_IMODE(stats.st_mode)
        desired_mode = stat.S_IRUSR + stat.S_IWUSR + stat.S_IXUSR

        self.assertEqual(actual_mode, desired_mode)

    @mock.patch('os.path.expanduser')
    @mock.patch('sys.stderr')
    def test_exists_with_wrong_perms(self, mock_stderr, mock_expanduser):
        mock_expanduser.return_value = self.pulppath
        os.mkdir(self.pulppath, 0755)

        launcher.ensure_user_pulp_dir()

        self.assertEqual(mock_stderr.write.call_count, 1)
        message = mock_stderr.write.call_args[0][0]
        # make sure it prints a warning to stderr
        self.assertTrue(message.startswith('Warning:'))

    @mock.patch('os.path.expanduser')
    @mock.patch('stat.S_IMODE', side_effect=TypeError)
    @mock.patch('sys.exit')
    @mock.patch('sys.stderr')
    def test_fail_to_access(self, mock_stderr, mock_exit, mock_stat, mock_expanduser):
        mock_expanduser.return_value = self.pulppath
        os.mkdir(self.pulppath, 0755)

        launcher.ensure_user_pulp_dir()

        mock_exit.assert_called_once_with(1)

        self.assertEqual(mock_stderr.write.call_count, 1)
        message = mock_stderr.write.call_args[0][0]
        # make sure it prints a warning to stderr
        self.assertTrue(message.startswith('Failed to access'))

    @mock.patch('os.path.expanduser')
    @mock.patch('os.mkdir', side_effect=ValueError)
    @mock.patch('sys.exit')
    @mock.patch('sys.stderr')
    def test_fail_to_create(self, mock_stderr, mock_exit, mock_mkdir, mock_expanduser):
        mock_expanduser.return_value = self.pulppath
        launcher.ensure_user_pulp_dir()

        mock_exit.assert_called_once_with(1)

        self.assertEqual(mock_stderr.write.call_count, 1)
        message = mock_stderr.write.call_args[0][0]
        # make sure it prints a warning to stderr
        self.assertTrue(message.startswith('Failed to create'))


class MyError(Exception):
    pass


class TestMain(unittest.TestCase):
    @mock.patch.object(launcher, 'ensure_user_pulp_dir', side_effect=MyError)
    def test_ensures_user_dir(self, mock_ensure_user_dir):
        """Just make sure it calls the ensure_user_pulp_dir function"""
        self.assertRaises(MyError, launcher.main, mock.MagicMock())
