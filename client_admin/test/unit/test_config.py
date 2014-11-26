from unittest import TestCase

from mock import call, Mock, patch

from pulp.client.admin.config import read_config, validate_overrides, SCHEMA, DEFAULT


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
    @patch('pulp.client.admin.config.validate_overrides')
    def test_read_calls_validate_overrides(self, mock_validate_overrides, fake_config):

        # test
        cfg = read_config()

        mock_validate_overrides.assert_called_once()

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

    @patch('pulp.client.admin.config.os.stat')
    @patch('pulp.client.admin.config.Config')
    def test_validate_overrides_when_has_password(self, mock_config, mock_os_stat):
        # st_mode is the file permissions component of stat output
        # st_mode = 33279 emulates a 777 permission
        mock_os_stat.return_value.st_mode = 33279
        mock_config.return_value.has_option.return_value = True
        self.assertRaises(RuntimeError, validate_overrides, '/tmp/admin.conf')
        mock_os_stat.assert_has_calls([call('/tmp/admin.conf')])
        mock_config.return_value.has_option.assert_called_once_with('auth', 'password')

    @patch('pulp.client.admin.config.os.stat')
    @patch('pulp.client.admin.config.Config')
    def test_validate_overrides_when_has_password_good_permissions(self, mock_config, mock_os_stat):
        # st_mode is the file permissions component of stat output
        # st_mode = 33216 emulates a 700 permission
        mock_os_stat.return_value.st_mode = 33216
        mock_config.return_value.has_option.return_value = True
        validate_overrides('/tmp/admin.conf')
        mock_config.assert_called_once_with('/tmp/admin.conf')

    @patch('pulp.client.admin.config.os.stat')
    @patch('pulp.client.admin.config.Config')
    def test_validate_overrides_when_does_not_have_password(self, mock_config, mock_os_stat):
        # st_mode is the file permissions component of stat output
        # st_mode = 33279 emulates a 777 permission
        mock_os_stat.return_value.st_mode = 33279
        mock_config.return_value.has_option.return_value = False
        try:
            validate_overrides('/tmp/admin.conf')
        except Exception as error:
            self.fail("validate_overrides should not raise an Exception. Raised %s" % error)
