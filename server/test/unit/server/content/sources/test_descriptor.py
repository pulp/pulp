from StringIO import StringIO
from unittest import TestCase

from mock import patch, Mock

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

    @patch('nectar.config.DownloaderConfig._process_ssl_settings', Mock())
    def test_nectar_config(self):
        descriptor = {
            constants.MAX_CONCURRENT: '10',
            constants.MAX_SPEED: '1024',
            constants.SSL_VALIDATION: 'true',
            constants.SSL_CA_CERT: 'ssl-ca-certificate',
            constants.SSL_CLIENT_KEY: 'ssl-client-key',
            constants.SSL_CLIENT_CERT: 'ssl-client-certificate',
            constants.PROXY_URL: 'proxy-url',
            constants.PROXY_PORT: '5000',
            constants.PROXY_USERID: 'proxy-userid',
            constants.PROXY_PASSWORD: 'proxy-password'
        }
        conf = nectar_config(descriptor)
        self.assertEqual(conf.max_concurrent, 10)
        self.assertEqual(conf.max_speed, 1024)
        self.assertEqual(conf.ssl_validation, True)
        self.assertEqual(conf.ssl_ca_cert_path, descriptor[constants.SSL_CA_CERT])
        self.assertEqual(conf.ssl_client_key_path, descriptor[constants.SSL_CLIENT_KEY])
        self.assertEqual(conf.ssl_client_cert_path, descriptor[constants.SSL_CLIENT_CERT])
        self.assertEqual(conf.proxy_url, descriptor[constants.PROXY_URL])
        self.assertEqual(conf.proxy_port, 5000)
        self.assertEqual(conf.proxy_username, descriptor[constants.PROXY_USERID])
        self.assertEqual(conf.proxy_password, descriptor[constants.PROXY_PASSWORD])
