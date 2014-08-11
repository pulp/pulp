"""
This module contains tests for the pulp.client.launcher module.
"""
import unittest

from pulp.client import launcher
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
