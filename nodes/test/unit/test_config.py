
from unittest import TestCase

from mock import patch

from pulp_node.config import read_config, SCHEMA, DEFAULT, NODE_CONFIGURATION_PATH


class TestConfig(TestCase):

    @staticmethod
    def schema_has_section(section):
        for _section in [s[0] for s in SCHEMA]:
            if _section == section:
                return True
        return False

    @staticmethod
    def schema_has_property(section, key):
        for _section in SCHEMA:
            if _section[0] != section:
                continue
            for _key in [p[0] for p in _section[2]]:
                if _key == key:
                    return True
        return False

    def test_default(self):
        # Everything in the schema has a default.
        for section in SCHEMA:
            for key in [p[0] for p in section[2]]:
                msg = '[%s] not found in schema' % key
                self.assertTrue(key in DEFAULT[section[0]], msg=msg)
        # Everything in the default is defined in the schema.
        for section in DEFAULT:
            self.assertTrue(self.schema_has_section(section))
            for key in DEFAULT[section]:
                msg = '[%s].%s has not default' % (section, key)
                self.assertTrue(self.schema_has_property(section, key), msg=msg)

    @patch('pulp_node.config.Config')
    def test_read(self, fake_config):
        # test
        cfg = read_config()

        # validation
        calls = fake_config.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][0], DEFAULT)
        self.assertEqual(calls[1][0][0], NODE_CONFIGURATION_PATH)
        fake_config().validate.assert_called_with(SCHEMA)
        self.assertEqual(cfg, fake_config().graph())

    @patch('pulp_node.config.Config')
    def test_read_path(self, fake_config):
        path = '/tmp/abc'

        # test
        cfg = read_config(path=path)

        # validation
        calls = fake_config.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][0], DEFAULT)
        self.assertEqual(calls[1][0][0], path)
        fake_config().validate.assert_called_with(SCHEMA)
        self.assertEqual(cfg, fake_config().graph())

    @patch('pulp_node.config.Config')
    def test_read_no_validation(self, fake_config):
        path = '/tmp/abc'

        # test
        cfg = read_config(path=path, validate=False)

        # validation
        calls = fake_config.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][0], DEFAULT)
        self.assertEqual(calls[1][0][0], path)
        self.assertFalse(fake_config().validate.called)
        self.assertEqual(cfg, fake_config().graph())
