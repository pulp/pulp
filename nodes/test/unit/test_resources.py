"""
This module contains tests for the pulp_node.resources module.
"""
import unittest

from pulp.common import config
import mock

from pulp_node import resources


class TestParentBindings(unittest.TestCase):
    """
    This class contains tests for the parent_bindings() function.
    """
    @mock.patch('pulp_node.resources.read_config')
    def test_verify_ssl_false(self, read_config):
        """
        Make sure that verify_ssl is passed correctly when it is false.
        """
        ca_path = '/some/path.crt'
        node_config = {'parent_oauth': {'key': 'some_key', 'secret': 'ssssh!', 'user_id': 'bgates'},
                       'main': {'verify_ssl': 'fAlsE', 'ca_path': ca_path}}
        node_config = config.Config(node_config).graph()
        read_config.return_value = node_config

        bindings = resources.parent_bindings('host')

        self.assertEqual(bindings.bindings.server.ca_path, ca_path)
        self.assertEqual(bindings.bindings.server.verify_ssl, False)

    @mock.patch('pulp_node.resources.read_config')
    def test_verify_ssl_true(self, read_config):
        """
        Make sure that verify_ssl is passed correctly when it is true.
        """
        ca_path = '/some/path'
        node_config = {'parent_oauth': {'key': 'some_key', 'secret': 'ssssh!', 'user_id': 'bgates'},
                       'main': {'verify_ssl': 'tRue', 'ca_path': ca_path}}
        node_config = config.Config(node_config).graph()
        read_config.return_value = node_config

        bindings = resources.parent_bindings('host')

        self.assertEqual(bindings.bindings.server.ca_path, ca_path)
        self.assertEqual(bindings.bindings.server.verify_ssl, True)


class TestPulpBindings(unittest.TestCase):
    """
    This class contains tests for the pulp_bindings() function.
    """
    @mock.patch('pulp_node.resources.read_config')
    def test_verify_ssl_false(self, read_config):
        """
        Make sure that verify_ssl is passed correctly when it is false.
        """
        ca_path = '/some/path.crt'
        node_config = {'parent_oauth': {'key': 'some_key', 'secret': 'ssssh!', 'user_id': 'bgates'},
                       'main': {'verify_ssl': 'fAlsE', 'ca_path': ca_path}}
        node_config = config.Config(node_config).graph()
        read_config.return_value = node_config

        bindings = resources.pulp_bindings()

        self.assertEqual(bindings.bindings.server.ca_path, ca_path)
        self.assertEqual(bindings.bindings.server.verify_ssl, False)

    @mock.patch('pulp_node.resources.read_config')
    def test_verify_ssl_true(self, read_config):
        """
        Make sure that verify_ssl is passed correctly when it is true.
        """
        ca_path = '/some/path'
        node_config = {'parent_oauth': {'key': 'some_key', 'secret': 'ssssh!', 'user_id': 'bgates'},
                       'main': {'verify_ssl': 'True', 'ca_path': ca_path}}
        node_config = config.Config(node_config).graph()
        read_config.return_value = node_config

        bindings = resources.pulp_bindings()

        self.assertEqual(bindings.bindings.server.ca_path, ca_path)
        self.assertEqual(bindings.bindings.server.verify_ssl, True)
