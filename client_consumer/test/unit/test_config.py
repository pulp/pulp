
from unittest import TestCase

from mock import patch, Mock

from pulp.client.consumer.config import read_config, SCHEMA, DEFAULT


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
                msg = '[%s].%s has no default' % (key, p[0])
                self.assertTrue(key in DEFAULT[section[0]], msg=msg)
        # Everything in the default is defined in the schema.
        for section in DEFAULT:
            self.assertTrue(self.schema_has_section(section))
            for key in DEFAULT[section]:
                msg = '[%s].%s has default but not found in the schema' % (section, key)
                self.assertTrue(self.schema_has_property(section, key), msg=msg)


    @patch('os.listdir')
    @patch('os.path.expanduser')
    @patch('os.path.exists', Mock(return_value=False))
    @patch('pulp.client.consumer.config.Config')
    def test_read(self, fake_config, fake_expanduser, fake_listdir):
        fake_listdir.return_value = ['A', 'B', 'C']
        fake_expanduser.return_value = '/home/pulp/.pulp/consumer.conf'

        # test
        cfg = read_config()

        # validation
        paths = [
            '/etc/pulp/consumer/consumer.conf',
            '/etc/pulp/consumer/conf.d/A',
            '/etc/pulp/consumer/conf.d/B',
            '/etc/pulp/consumer/conf.d/C',
        ]

        fake_config.assert_called_with(*paths)
        fake_config().validate.assert_called_with(SCHEMA)
        self.assertEqual(cfg, fake_config())

    @patch('pulp.client.consumer.config.Config')
    def test_read_paths(self, fake_config):
        paths = ['path_A', 'path_B']

        # test
        cfg = read_config(paths=paths)

        # validation
        fake_config.assert_called_with(*paths)
        fake_config().validate.assert_called_with(SCHEMA)
        self.assertEqual(cfg, fake_config())

    @patch('pulp.client.consumer.config.Config')
    def test_read_no_validation(self, fake_config):
        paths = ['path_A', 'path_B']

        # test
        cfg = read_config(paths=paths, validate=False)

        # validation
        fake_config.assert_called_with(*paths)
        self.assertFalse(fake_config().validate.called)
        self.assertEqual(cfg, fake_config())

    @patch('os.listdir')
    @patch('os.path.expanduser')
    @patch('os.path.exists', Mock(return_value=True))
    @patch('pulp.client.consumer.config.Config')
    def test_read_with_override(self, fake_config, fake_expanduser, fake_listdir):
        fake_listdir.return_value = ['A', 'B', 'C']
        fake_expanduser.return_value = '/home/pulp/.pulp/consumer.conf'

        # test
        cfg = read_config()

        # validation
        paths = [
            '/etc/pulp/consumer/consumer.conf',
            '/etc/pulp/consumer/conf.d/A',
            '/etc/pulp/consumer/conf.d/B',
            '/etc/pulp/consumer/conf.d/C',
            '/home/pulp/.pulp/consumer.conf'
        ]

        fake_config.assert_called_with(*paths)
        fake_config().validate.assert_called_with(SCHEMA)
        self.assertEqual(cfg, fake_config())
