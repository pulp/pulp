
import os
import os.path
import tempfile

from unittest import TestCase

from mock import patch, Mock

from pulp.client.admin.config import read_config, SCHEMA, DEFAULT


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

    @patch('os.listdir')
    @patch('os.path.expanduser')
    @patch('os.path.exists', Mock(return_value=False))
    @patch('pulp.client.admin.config.Config')
    def test_read(self, fake_config, fake_expanduser, fake_listdir):
        fake_listdir.return_value = ['A', 'B', 'C']
        fake_expanduser.return_value = '/home/pulp/.pulp/admin.conf'

        # test
        cfg = read_config()

        # validation
        paths = [
            '/etc/pulp/admin/admin.conf',
            '/etc/pulp/admin/conf.d/A',
            '/etc/pulp/admin/conf.d/B',
            '/etc/pulp/admin/conf.d/C',
        ]

        fake_config.assert_called_with(*paths)
        fake_config().validate.assert_called_with(SCHEMA)
        self.assertEqual(cfg, fake_config())

    @patch('pulp.client.admin.config.Config')
    def test_read_paths(self, fake_config):
        paths = ['path_A', 'path_B']

        # test
        cfg = read_config(paths=paths)

        # validation
        fake_config.assert_called_with(*paths)
        fake_config().validate.assert_called_with(SCHEMA)
        self.assertEqual(cfg, fake_config())

    @patch('pulp.client.admin.config.Config')
    def test_read_no_validation(self, fake_config):
        paths = ['path_A', 'path_B']

        # test
        cfg = read_config(paths=paths, validate=False)

        # validation
        fake_config.assert_called_with(*paths)
        self.assertFalse(fake_config().validate.called)
        self.assertEqual(cfg, fake_config())

    @patch('pulp.client.admin.config.validate_overrides', Mock(return_value=True))
    @patch('os.listdir')
    @patch('os.path.expanduser')
    @patch('os.path.exists', Mock(return_value=True))
    @patch('pulp.client.admin.config.Config')
    def test_read_with_override(self, fake_config, fake_expanduser, fake_listdir):
        fake_listdir.return_value = ['A', 'B', 'C']
        fake_expanduser.return_value = '/home/pulp/.pulp/admin.conf'

        # test
        cfg = read_config()

        # validation
        paths = [
            '/etc/pulp/admin/admin.conf',
            '/etc/pulp/admin/conf.d/A',
            '/etc/pulp/admin/conf.d/B',
            '/etc/pulp/admin/conf.d/C',
            '/home/pulp/.pulp/admin.conf'
        ]

        fake_config.assert_called_with(*paths)
        fake_config().validate.assert_called_with(SCHEMA)
        self.assertEqual(cfg, fake_config())

    @patch('os.listdir')
    @patch('os.path.expanduser')
    @patch('pulp.client.admin.config.Config')
    def test_validate_overrides_when_has_password(self,
                                                  fake_config,
                                                  fake_expanduser,
                                                  fake_listdir):
        # we are trying to fake Config.has_option return True
        # so it means config file has password
        fake_instance = fake_config.return_value

        def has_option(*args):
            return True

        fake_instance.has_option = has_option

        fn = tempfile.NamedTemporaryFile()
        fake_expanduser.return_value = fn.name

        os.chmod(fn.name, 0777)
        fake_listdir.return_value = ['A', 'B', 'C']
        self.assertRaises(RuntimeError, read_config)

        #validation
        paths = [fn.name]

        # Config is only called from within
        # pulp.client.admin.config.validate_overrides
        # not not from read_config as it would have exited
        # after throwing exception when config has password
        # and file is world readable
        fake_config.assert_called_with(*paths)
        self.assertFalse(fake_config().validate.called)

    @patch('os.listdir')
    @patch('os.path.expanduser')
    @patch('pulp.client.admin.config.Config')
    def test_validate_overrides_when_does_not_have_password(self,
                                                            fake_config,
                                                            fake_expanduser,
                                                            fake_listdir):
        # we are trying to fake Config.has_option return False
        # so it means config file does not have password
        fake_instance = fake_config.return_value

        def has_option(*args): return False
        fake_instance.has_option = has_option

        fn = tempfile.NamedTemporaryFile()
        fake_expanduser.return_value = fn.name

        os.chmod(fn.name, 0777)
        fake_listdir.return_value = ['A', 'B', 'C']
        cfg = read_config()

        #validation
        paths = [
            '/etc/pulp/admin/admin.conf',
            '/etc/pulp/admin/conf.d/A',
            '/etc/pulp/admin/conf.d/B',
            '/etc/pulp/admin/conf.d/C',
            fn.name,
        ]
        fake_config.assert_called_with(*paths)
        fake_config().validate.assert_called_with(SCHEMA)
        self.assertEqual(cfg, fake_config())
