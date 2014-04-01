# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase
from StringIO import StringIO

from pulp.common.config import Config
from pulp.server.content.sources import constants
from pulp.server.content.sources.descriptor import is_valid, to_seconds, nectar_config

UNIT_WORLD = 'unit-world'

VALID = """
[%s]
enabled: 1
type: yum
name: Unit World
priority: 1
max_concurrent: 10
base_url: file:///unit-world/
""" % UNIT_WORLD

MISSING_ENABLED = """
[missing-enabled]
type: yum
name: Test Invalid
priority: 2
base_url: http:///invalid/
"""

MISSING_TYPE = """
[missing-type]
enabled: 1
name: Test Invalid
priority: 2
base_url: http:///invalid/
"""

MISSING_BASE_URL = """
[missing-base_url]
enabled: 1
type: yum
name: Test Invalid
priority: 2
"""


class TestDescriptor(TestCase):

    def test_to_seconds(self):
        self.assertEqual(to_seconds('10'), 10)
        self.assertEqual(to_seconds('10s'), 10)
        self.assertEqual(to_seconds('10m'), 600)
        self.assertEqual(to_seconds('10h'), 36000)
        self.assertEqual(to_seconds('10d'), 864000)

    def test_valid(self):
        fp = StringIO(VALID)
        config = Config(fp)
        for source_id, descriptor in config.items():
            self.assertTrue(is_valid(source_id, descriptor))

    def test_invalid(self):
        for s in (MISSING_ENABLED, MISSING_TYPE, MISSING_BASE_URL):
            fp = StringIO(s)
            config = Config(fp)
            for source_id, descriptor in config.items():
                self.assertFalse(is_valid(source_id, descriptor))

    def test_nectar_config(self):
        descriptor = {
            constants.MAX_CONCURRENT: '10',
            constants.MAX_SPEED: '1000',
            constants.SSL_VALIDATION: 'True',
            constants.SSL_CA_CERT: '/my-ca-cert',
            constants.SSL_CLIENT_CERT: '/my-client-cert',
            constants.SSL_CLIENT_KEY: '/my-client-key',
            constants.PROXY_URL: '/my-proxy-url',
            constants.PROXY_PORT: '9090',
            constants.PROXY_USERID: 'proxy-user',
            constants.PROXY_PASSWORD: 'proxy-password',
            constants.HEADERS: {'A': 1},
        }

        # test

        conf = nectar_config(descriptor)

        # validation

        for key, function in constants.NECTAR_PROPERTIES:
            self.assertTrue(key in descriptor, msg=key)
            self.assertEqual(function(descriptor[key]), getattr(conf, key))