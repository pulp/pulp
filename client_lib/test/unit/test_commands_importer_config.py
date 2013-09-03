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

import os

from pulp.client.commands.repo import importer_config
from pulp.client.extensions.extensions import PulpCliCommand
from pulp.common.plugins import importer_constants as constants
from pulp.devel.unit import base


FILES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                         '../data', 'test_commands_importer_config')


class MixinTest(PulpCliCommand, importer_config.ImporterConfigMixin):
    """
    The mixin can't be used alone so this class has the proper usage to run. When the command is
    executed, it will stored the parsed version of the config to be accessed by an assertion.
    """

    def __init__(self, options_bundle=None, include_sync=True, include_ssl=True, include_proxy=True,
                 include_throttling=True, include_unit_policy=True):
        PulpCliCommand.__init__(self, 'mixin', '', self.run)
        importer_config.ImporterConfigMixin.__init__(self,
                                                     options_bundle=options_bundle,
                                                     include_sync=include_sync,
                                                     include_ssl=include_ssl,
                                                     include_proxy=include_proxy,
                                                     include_throttling=include_throttling,
                                                     include_unit_policy=include_unit_policy)

        self.last_parsed_config = None

    def run(self, **kwargs):
        self.last_parsed_config = self.parse_user_input(kwargs)


class ImporterConfigMixinTests(base.PulpClientTests):

    def setUp(self):
        super(ImporterConfigMixinTests, self).setUp()
        self.mixin = MixinTest()

    def test_custom_options_bundle(self):
        # Test
        new_options_bundle = importer_config.OptionsBundle()
        self.mixin = MixinTest(options_bundle=new_options_bundle)

        # Verify
        self.assertTrue(self.mixin.options_bundle is new_options_bundle)

    def test_groups(self):
        """
        Verify the groups are added to the command. The contents of those groups will be
        tested separately.
        """

        self.assertEqual(5, len(self.mixin.option_groups))
        group_names = [g.name for g in self.mixin.option_groups]
        expected_names = [importer_config.GROUP_NAME_SYNC, importer_config.GROUP_NAME_SSL,
                          importer_config.GROUP_NAME_PROXY, importer_config.GROUP_NAME_THROTTLING,
                          importer_config.GROUP_NAME_UNIT_POLICY]
        self.assertEqual(set(group_names), set(expected_names))

    def test_groups_no_includes(self):
        self.mixin = MixinTest(include_sync=False, include_ssl=False, include_proxy=False,
                               include_throttling=False, include_unit_policy=False)
        self.assertEqual(0, len(self.mixin.option_groups))

    # -- populate tests -------------------------------------------------------

    def test_populate_sync_group(self):
        group = [g for g in self.mixin.option_groups if g.name == importer_config.GROUP_NAME_SYNC][0]
        options = group.options

        self.assertEqual(2, len(options))
        self.assertEqual(options[0], self.mixin.options_bundle.opt_feed)
        self.assertEqual(options[1], self.mixin.options_bundle.opt_validate)

    def test_populate_ssl_group(self):
        group = [g for g in self.mixin.option_groups if g.name == importer_config.GROUP_NAME_SSL][0]
        options = group.options

        self.assertEqual(4, len(options))
        self.assertEqual(options[0], self.mixin.options_bundle.opt_feed_ca_cert)
        self.assertEqual(options[1], self.mixin.options_bundle.opt_verify_feed_ssl)
        self.assertEqual(options[2], self.mixin.options_bundle.opt_feed_cert)
        self.assertEqual(options[3], self.mixin.options_bundle.opt_feed_key)

    def test_populate_proxy_group(self):
        group = [g for g in self.mixin.option_groups if g.name == importer_config.GROUP_NAME_PROXY][0]
        options = group.options

        self.assertEqual(4, len(options))
        self.assertEqual(options[0], self.mixin.options_bundle.opt_proxy_host)
        self.assertEqual(options[1], self.mixin.options_bundle.opt_proxy_port)
        self.assertEqual(options[2], self.mixin.options_bundle.opt_proxy_user)
        self.assertEqual(options[3], self.mixin.options_bundle.opt_proxy_pass)

    def test_populate_throttling_group(self):
        group = [g for g in self.mixin.option_groups if g.name == importer_config.GROUP_NAME_THROTTLING][0]
        options = group.options

        self.assertEqual(2, len(options))
        self.assertEqual(options[0], self.mixin.options_bundle.opt_max_downloads)
        self.assertEqual(options[1], self.mixin.options_bundle.opt_max_speed)

    # -- parse tests ----------------------------------------------------------

    def test_parse_sync_group(self):
        # Setup
        user_input = {
            self.mixin.options_bundle.opt_feed.keyword : 'feed-1',
            self.mixin.options_bundle.opt_validate.keyword : True,
        }

        # Test
        parsed = self.mixin.parse_sync_group(user_input)

        # Verify
        self.assertEqual(2, len(parsed))
        self.assertEqual(parsed[constants.KEY_FEED], 'feed-1')
        self.assertEqual(parsed[constants.KEY_VALIDATE], True)

    def test_parse_ssl_group(self):
        # Setup
        user_input = {
            self.mixin.options_bundle.opt_feed_ca_cert.keyword : os.path.join(FILES_DIR, 'ca_cert.crt'),
            self.mixin.options_bundle.opt_verify_feed_ssl.keyword : True,
            self.mixin.options_bundle.opt_feed_cert.keyword : os.path.join(FILES_DIR, 'client_cert.crt'),
            self.mixin.options_bundle.opt_feed_key.keyword : os.path.join(FILES_DIR, 'client_key.crt'),
        }

        # Test
        parsed = self.mixin.parse_ssl_group(user_input)

        # Verify
        self.assertEqual(4, len(parsed))
        self.assertEqual(parsed['ssl_ca_cert'], 'ca_cert\n')
        self.assertEqual(parsed['ssl_validation'], True)
        self.assertEqual(parsed['ssl_client_cert'], 'client_cert\n')
        self.assertEqual(parsed['ssl_client_key'], 'client_key\n')

    def test_parse_proxy_group(self):
        # Setup
        user_input = {
            self.mixin.options_bundle.opt_proxy_host.keyword : 'host-1',
            self.mixin.options_bundle.opt_proxy_port.keyword : 80,
            self.mixin.options_bundle.opt_proxy_user.keyword : 'user-1',
            self.mixin.options_bundle.opt_proxy_pass.keyword : 'pass-1',
        }

        # Test
        parsed = self.mixin.parse_proxy_group(user_input)

        # Verify
        self.assertEqual(4, len(parsed))
        self.assertEqual(parsed['proxy_host'], 'host-1')
        self.assertEqual(parsed['proxy_port'], 80)
        self.assertEqual(parsed['proxy_username'], 'user-1')
        self.assertEqual(parsed['proxy_password'], 'pass-1')

    def test_parse_throttling(self):
        # Setup
        user_input = {
            self.mixin.options_bundle.opt_max_speed.keyword : 1024,
            self.mixin.options_bundle.opt_max_downloads.keyword : 4,
        }

        # Test
        parsed = self.mixin.parse_throttling_group(user_input)

        # Verify
        self.assertEqual(2, len(parsed))
        self.assertEqual(parsed['max_downloads'], 4)
        self.assertEqual(parsed['max_speed'], 1024)

    def test_end_to_end(self):
        # Setup
        self.cli.add_command(self.mixin)
        user_input = 'mixin --feed url --proxy-host phost --verify-feed-ssl true ' \
                     '--max-downloads 5 --remove-missing true'

        # Test
        self.cli.run(user_input.split())

        # Verify
        self.assertEqual(self.mixin.last_parsed_config['feed'], 'url')
        self.assertEqual(self.mixin.last_parsed_config['proxy_host'], 'phost')
        self.assertEqual(self.mixin.last_parsed_config['ssl_validation'], True)
        self.assertEqual(self.mixin.last_parsed_config['max_downloads'], 5)
        self.assertEqual(self.mixin.last_parsed_config['remove_missing'], True)
