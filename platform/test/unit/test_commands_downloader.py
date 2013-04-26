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

import base
from pulp.client.commands.repo import downloader
from pulp.client.extensions.extensions import PulpCliCommand


FILES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'test_commands_downloader')


class MixinTest(PulpCliCommand, downloader.DownloaderConfigMixin):
    """
    The mixin can't be used alone so this class has the proper usage to run. When the command is
    executed, it will stored the parsed version of the config to be accessed by an assertion.
    """

    def __init__(self, include_ssl=True, include_proxy=True, include_throttling=True):
        PulpCliCommand.__init__(self, 'mixin', '', self.run)
        downloader.DownloaderConfigMixin.__init__(self, include_ssl, include_proxy, include_throttling)

        self.last_parsed_config = None

    def run(self, **kwargs):
        self.last_parsed_config = self.parse_user_input(kwargs)


class DownloaderMixinTests(base.PulpClientTests):

    def setUp(self):
        super(DownloaderMixinTests, self).setUp()
        self.mixin = MixinTest()

    def test_groups(self):
        """
        Verify the groups are added to the command. The contents of those groups will be
        tested separately.
        """

        self.assertEqual(3, len(self.mixin.option_groups))
        group_names = [g.name for g in self.mixin.option_groups]
        expected_names = [downloader.GROUP_NAME_SSL, downloader.GROUP_NAME_PROXY,
                          downloader.GROUP_NAME_THROTTLING]
        self.assertEqual(set(group_names), set(expected_names))

    def test_groups_no_includes(self):
        self.mixin = MixinTest(include_ssl=False, include_proxy=False, include_throttling=False)
        self.assertEqual(0, len(self.mixin.option_groups))

    # -- populate tests -------------------------------------------------------

    def test_populate_ssl_group(self):
        group = [g for g in self.mixin.option_groups if g.name == downloader.GROUP_NAME_SSL][0]
        options = group.options

        self.assertEqual(4, len(options))
        self.assertEqual(options[0], downloader.OPT_FEED_CA_CERT)
        self.assertEqual(options[1], downloader.OPT_VERIFY_FEED_SSL)
        self.assertEqual(options[2], downloader.OPT_FEED_CERT)
        self.assertEqual(options[3], downloader.OPT_FEED_KEY)

    def test_populate_proxy_group(self):
        group = [g for g in self.mixin.option_groups if g.name == downloader.GROUP_NAME_PROXY][0]
        options = group.options

        self.assertEqual(4, len(options))
        self.assertEqual(options[0], downloader.OPT_PROXY_HOST)
        self.assertEqual(options[1], downloader.OPT_PROXY_PORT)
        self.assertEqual(options[2], downloader.OPT_PROXY_USER)
        self.assertEqual(options[3], downloader.OPT_PROXY_PASS)

    def test_populate_throttling_group(self):
        group = [g for g in self.mixin.option_groups if g.name == downloader.GROUP_NAME_THROTTLING][0]
        options = group.options

        self.assertEqual(2, len(options))
        self.assertEqual(options[0], downloader.OPT_MAX_DOWNLOADS)
        self.assertEqual(options[1], downloader.OPT_MAX_SPEED)

    # -- parse tests ----------------------------------------------------------

    def test_parse_ssl_group(self):
        # Setup
        user_input = {
            downloader.OPT_FEED_CA_CERT.keyword : os.path.join(FILES_DIR, 'ca_cert.crt'),
            downloader.OPT_VERIFY_FEED_SSL.keyword : True,
            downloader.OPT_FEED_CERT.keyword : os.path.join(FILES_DIR, 'client_cert.crt'),
            downloader.OPT_FEED_KEY.keyword : os.path.join(FILES_DIR, 'client_key.crt'),
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
            downloader.OPT_PROXY_HOST.keyword : 'host-1',
            downloader.OPT_PROXY_PORT.keyword : 80,
            downloader.OPT_PROXY_USER.keyword : 'user-1',
            downloader.OPT_PROXY_PASS.keyword : 'pass-1',
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
            downloader.OPT_MAX_SPEED.keyword : 1024,
            downloader.OPT_MAX_DOWNLOADS.keyword : 4,
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
        user_input = 'mixin --proxy-host phost --verify-feed-ssl true --max-downloads 5'

        # Test
        self.cli.run(user_input.split())

        # Verify
        self.assertEqual(self.mixin.last_parsed_config['proxy_host'], 'phost')
        self.assertEqual(self.mixin.last_parsed_config['ssl_validation'], True)
        self.assertEqual(self.mixin.last_parsed_config['max_downloads'], 5)
