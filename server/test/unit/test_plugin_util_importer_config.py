# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from inspect import getmembers, isfunction
import unittest

import mock

from pulp.common.plugins import importer_constants
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.util import importer_config


class MainMethodTests(unittest.TestCase):

    def test_all_pass(self):
        # All options are optional, so we can run them without concern
        config = PluginCallConfiguration({}, {})
        importer_config.validate_config(config)
        # no exception should be raised

    def test_failure(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_VALIDATE : 0})
        self.assertRaises(importer_config.InvalidConfig, importer_config.validate_config, config)

    def test_validation_step_list(self):
        """
        Make sure all of the _validate_* methods are listed in the VALIDATIONS constant to
        be run.
        """
        # Function names from the module itself
        functions_list = [f for f in getmembers(importer_config, isfunction)]
        validate_step_function_names = [f[0] for f in functions_list if f[0].startswith('validate') and
                                                                        f[0] != 'validate_config']

        # Function names from the driver constant
        found_step_function_names = [f.__name__ for f in importer_config.VALIDATIONS]

        self.assertEqual(set(validate_step_function_names), set(found_step_function_names))


class FeedTests(unittest.TestCase):

    def test_valid(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_FEED: "http://test.com/feed"})
        importer_config.validate_feed_requirement(config)
        # no exception should be raised

    def test_invalid(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_FEED: 42})
        try:
            importer_config.validate_feed_requirement(config)
            self.fail()
        except ValueError, e:
            self.assertTrue(importer_constants.KEY_FEED in e[0])

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_feed_requirement(config)
        # no exception should be raised


class MaxSpeedTests(unittest.TestCase):

    def test_int(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_MAX_SPEED: 1})
        importer_config.validate_max_speed(config)
        # test ensures no exception raised

    def test_str(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_MAX_SPEED: '512'})
        importer_config.validate_max_speed(config)
        # test ensures no exception raised

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_max_speed(config)
        # no exception should be raised

    def test_non_positive(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_MAX_SPEED: -1})
        try:
            importer_config.validate_max_speed(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('parameter <max_speed>' in e[0])
            self.assertTrue('-1' in e[0])

    def test_non_positive_str(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_MAX_SPEED: '-42'})
        try:
            importer_config.validate_max_speed(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('parameter <max_speed>' in e[0])
            self.assertTrue('-42' in e[0])


class MaxDownloadsTests(unittest.TestCase):

    def test_validate(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_MAX_DOWNLOADS: 11})
        importer_config.validate_max_downloads(config)
        # no exception should be raised

    def test_validate_str(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_MAX_DOWNLOADS: '2'})
        importer_config.validate_max_downloads(config)
        # no exception should be raised

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_max_downloads(config)
        # no exception should be raised

    def test_float(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_MAX_DOWNLOADS: 1.1})
        try:
            importer_config.validate_max_downloads(config)
            self.fail()
        except ValueError, e:
            self.assertTrue(importer_constants.KEY_MAX_DOWNLOADS in e[0])
            self.assertTrue('1.1' in e[0])

    def test_float_str(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_MAX_DOWNLOADS: '1.1'})
        try:
            importer_config.validate_max_downloads(config)
            self.fail()
        except ValueError, e:
            self.assertTrue(importer_constants.KEY_MAX_DOWNLOADS in e[0])
            self.assertTrue('1.1' in e[0])

    def test_zero(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_MAX_DOWNLOADS: 0})
        try:
            importer_config.validate_max_downloads(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('0' in e[0])


class ProxyHostTests(unittest.TestCase):

    def test_validate(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_HOST: 'http://fake.com/'})
        importer_config.validate_proxy_host(config)
        # no exception should be raised

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_proxy_host(config)
        # no exception should be raised

    def test_required_when_other_parameters_are_present(self):

        dependent_parameters = (
            {importer_constants.KEY_PROXY_PASS : 'pass-1'},
            {importer_constants.KEY_PROXY_USER : 'user-1'},
            {importer_constants.KEY_PROXY_PORT : 8080},
        )

        for parameters in dependent_parameters:
                # Each of the above configurations should cause the validator to complain about
                # the proxy_url missing
                config = PluginCallConfiguration({}, parameters)
                try:
                    importer_config.validate_proxy_host(config)
                    self.fail()
                except ValueError, e:
                    self.assertTrue(importer_constants.KEY_PROXY_HOST in e[0])

    def test_host_is_non_string(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_HOST: 7})
        try:
            importer_config.validate_proxy_host(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('int' in e[0])


class ProxyPortTests(unittest.TestCase):

    def test_valid(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_PORT: 8088})
        importer_config.validate_proxy_port(config)
        # no exception should be raised

    def test_valid_str(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_PORT: '3128'})
        importer_config.validate_proxy_port(config)
        # no exception should be raised

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_proxy_port(config)
        # no exception should be raised

    def test_less_than_one(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_PORT: 0})
        try:
            importer_config.validate_proxy_port(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('0' in e[0])

    def test_non_string(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_PORT: 1.1})
        try:
            importer_config.validate_proxy_port(config)
        except ValueError, e:
            self.assertTrue('1.1' in e[0])


class ProxyUsernameTests(unittest.TestCase):

    def test_valid(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_PASS: 'duderino',
                                              importer_constants.KEY_PROXY_USER: 'the_dude'})
        importer_config.validate_proxy_username(config)
        # no exception should be raised

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_proxy_username(config)
        # no exception should be raised

    def test_password_no_username(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_PASS: 'the_dude'})
        try:
            importer_config.validate_proxy_username(config)
            self.fail()
        except ValueError, e:
            self.assertTrue(importer_constants.KEY_PROXY_USER in e[0])
            self.assertTrue(importer_constants.KEY_PROXY_PASS in e[0])

    def test_username_is_non_string(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_USER: 185})
        try:
            importer_config.validate_proxy_username(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('int' in e[0])


class ProxyPasswordTests(unittest.TestCase):

    def test_valid(self):
        config = PluginCallConfiguration({},
            {importer_constants.KEY_PROXY_PASS: 'duderino',
             importer_constants.KEY_PROXY_USER: 'the_dude'})
        importer_config.validate_proxy_password(config)
        # no exception should be raised

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_proxy_password(config)
        # no exception should be raised

    def test_username_no_password(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_USER: 'user-1'})
        try:
            importer_config.validate_proxy_password(config)
            self.fail()
        except ValueError, e:
            self.assertTrue(importer_constants.KEY_PROXY_USER in e[0])
            self.assertTrue(importer_constants.KEY_PROXY_PASS in e[0])

    def test_password_is_non_string(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_PROXY_PASS: 7,
                                              importer_constants.KEY_PROXY_USER: 'user-1'})
        try:
            importer_config.validate_proxy_password(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('int' in e[0])


class SSLValidationFlagTests(unittest.TestCase):

    @mock.patch('pulp.plugins.util.importer_config._run_validate_is_non_required_bool')
    def test_delegate(self, mock_util):
        importer_config.validate_ssl_validation_flag('config')
        mock_util.assert_called_once_with('config', importer_constants.KEY_SSL_VALIDATION)


class SSLCACertTests(unittest.TestCase):

    def test_valid(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_SSL_CA_CERT : 'cert'})
        importer_config.validate_ssl_ca_cert(config)
        # no exception should be raised

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_ssl_ca_cert(config)
        # no exception should be raised

    def test_ca_cert_is_non_string(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_SSL_CA_CERT: 7})
        try:
            importer_config.validate_ssl_ca_cert(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('int' in e[0])


class SSLClientCertTests(unittest.TestCase):

    def test_valid(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_SSL_CLIENT_CERT : 'cert'})
        importer_config.validate_ssl_client_cert(config)
        # no exception should be raised

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_ssl_client_cert(config)
        # no exception should be raised

    def test_client_cert_is_non_string(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_SSL_CLIENT_CERT: 8})
        try:
            importer_config.validate_ssl_client_cert(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('int' in e[0])

    def test_client_key_requires_client_cert(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_SSL_CLIENT_KEY: 'key'})
        try:
            importer_config.validate_ssl_client_cert(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('ssl_client_cert' in e[0])


class SSLClientKeyTests(unittest.TestCase):

    def test_valid(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_SSL_CLIENT_KEY : 'key'})
        importer_config.validate_ssl_client_key(config)
        # no exception should be raised

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_ssl_client_key(config)
        # no exception should be raised

    def test_client_key_is_non_string(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_SSL_CLIENT_KEY: 9})
        try:
            importer_config.validate_ssl_client_key(config)
            self.fail()
        except ValueError, e:
            self.assertTrue('int' in e[0])


class ValidateDownloadsTests(unittest.TestCase):

    @mock.patch('pulp.plugins.util.importer_config._run_validate_is_non_required_bool')
    def test_delegate(self, mock_util):
        importer_config.validate_validate_downloads('config')
        mock_util.assert_called_once_with('config', importer_constants.KEY_VALIDATE)


class RemoveMissingTests(unittest.TestCase):

    @mock.patch('pulp.plugins.util.importer_config._run_validate_is_non_required_bool')
    def test_delegate(self, mock_util):
        importer_config.validate_remove_missing('config')
        mock_util.assert_called_once_with('config', importer_constants.KEY_UNITS_REMOVE_MISSING)


class RetainOldCountTests(unittest.TestCase):

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config.validate_retain_old_count(config)
        # no exception should be raised

    def test_int(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_UNITS_RETAIN_OLD_COUNT: 1})
        importer_config.validate_retain_old_count(config)
        # test ensures no exception raised

    def test_str(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_UNITS_RETAIN_OLD_COUNT: '1'})
        importer_config.validate_retain_old_count(config)
        # test ensures no exception raised

    def test_non_positive(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_UNITS_RETAIN_OLD_COUNT: -1})
        try:
            importer_config.validate_retain_old_count(config)
            self.fail()
        except ValueError, e:
            self.assertTrue(importer_constants.KEY_UNITS_RETAIN_OLD_COUNT in e[0])
            self.assertTrue('-1' in e[0])

    def test_non_positive_str(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_UNITS_RETAIN_OLD_COUNT: '-1'})
        try:
            importer_config.validate_retain_old_count(config)
            self.fail()
        except ValueError, e:
            self.assertTrue(importer_constants.KEY_UNITS_RETAIN_OLD_COUNT in e[0])
            self.assertTrue('-1' in e[0])


class ValidateIsNonRequiredBooleanTests(unittest.TestCase):

    def test_valid_bool(self):
        config = PluginCallConfiguration({}, {'a' : True})
        importer_config._run_validate_is_non_required_bool(config, 'a')
        # no exception should be raised

    def test_valid_str(self):
        config = PluginCallConfiguration({}, {'a' : 'true'})
        importer_config._run_validate_is_non_required_bool(config, 'a')
        # no exception should be raised

    def test_optional(self):
        config = PluginCallConfiguration({}, {})
        importer_config._run_validate_is_non_required_bool(config, 'missing')
        # no exception should be raised

    def test_unparsable(self):
        config = PluginCallConfiguration({}, {'a' : 'x'})
        try:
            importer_config._run_validate_is_non_required_bool(config, 'a')
            self.fail()
        except ValueError, e:
            self.assertTrue('x' in e[0])
