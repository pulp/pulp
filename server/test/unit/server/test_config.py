import __builtin__
import mock
import os
import shutil
import tempfile
from collections import defaultdict
from functools import partial

from pulp.common.compat import unittest
from pulp.devel.unit.server.base import (block_load_conf, override_config_attrs,
                                         restore_config_attrs)
from pulp.server import config

# a fake config with a new section and one that overrides a default
FAKE_CONFIG_1 = '''\
[section1]
key1 = value1

[server]
test_key = test_value
server_name = foo
'''

# another fake config
FAKE_CONFIG_2 = '''\
[section1]
key2 = value2

[section2]
key1 = value3
'''

# save the existing config to restore when we're done messing with it
initial_config_files = config._config_files
initial_config_object = config.config


class ConfigFileMock(object):
    # This is defined in the static scope of the class to deal with tracking
    # all calls to open in a single test across multiple instances;
    # use (mock_instance).load_counts.clear() to reset its state
    load_counts = defaultdict(int)

    # the available version of mock.mock_open doesn't support the readline method,
    # so this is a custom mock designed just for tracking config file loads,
    # supporting only the file interface that ConfigParsers actually use
    def __init__(self, name, *args, **kwargs):
        # we're mocking open, so open doesn't work here
        self.real_file = os.fdopen(os.open(name, os.O_RDWR), *args, **kwargs)
        self.load_counts[name] += 1

    def readline(self):
        return self.real_file.readline()

    def close(self):
        self.real_file.close()


class TestDefaultConfigFiles(unittest.TestCase):
    @mock.patch.object(__builtin__, 'open')
    def test_config_not_loaded(self, mock_open):
        # We mess with the default config files *a lot* in following tests,
        # so we ought to make sure the defaults are sane before messing around

        # reload the module to make sure any of the aforementioned messing
        # is un-done before we start testing it
        reload(config)

        # open wasn't called during module load
        self.assertEqual(mock_open.call_count, 0)

        # _config_files is what we expect
        self.assertEqual(config._config_files, ['/etc/pulp/server.conf'])

        # config is the right type
        self.assertIsInstance(config.config, config.LazyConfigParser)

    def tearDown(self):
        block_load_conf()


class TestLoadConfFromFiles(unittest.TestCase):
    def setUp(self):
        restore_config_attrs()
        self.addCleanup(override_config_attrs)

        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(partial(shutil.rmtree, self.tmpdir))

        config_1_fh, self.config_1_name = tempfile.mkstemp(dir=self.tmpdir)
        config_1 = os.fdopen(config_1_fh, 'w')
        config_1.write(FAKE_CONFIG_1)
        config_1.close()

        config_2_fh, self.config_2_name = tempfile.mkstemp(dir=self.tmpdir)
        config_2 = os.fdopen(config_2_fh, 'w')
        config_2.write(FAKE_CONFIG_2)
        config_2.close()

        # teh spoofs (spooves?)
        config._config_files = [self.config_1_name, self.config_2_name]
        config.config = config.LazyConfigParser()
        ConfigFileMock.load_counts.clear()

    @classmethod
    def tearDownClass(self):
        # we were never here...restore the saved config methods
        config._config_files = initial_config_files
        config.config = initial_config_object

    @mock.patch.object(__builtin__, 'open', ConfigFileMock)
    def test_file_load_counts(self):
        self.assertEqual(open.load_counts[self.config_1_name], 0)
        self.assertEqual(open.load_counts[self.config_2_name], 0)
        self.assertFalse(config.config._loaded)

        config.config.sections()
        # open was called, config is loaded
        self.assertEqual(open.load_counts[self.config_1_name], 1)
        self.assertEqual(open.load_counts[self.config_2_name], 1)
        self.assertTrue(config.config._loaded)

        config.config.sections()
        # open wasn't called again, config already loaded
        self.assertEqual(open.load_counts[self.config_1_name], 1)
        self.assertEqual(open.load_counts[self.config_2_name], 1)
        self.assertTrue(config.config._loaded)

        config.load_configuration()
        config.config.sections()
        # open was called again, config was reloaded
        self.assertEqual(open.load_counts[self.config_1_name], 2)
        self.assertEqual(open.load_counts[self.config_2_name], 2)

        # Both config files were loaded
        self.assertEqual(len(open.load_counts), 2)

    @mock.patch.object(__builtin__, 'open', ConfigFileMock)
    def test_file_contents(self):
        default_sections = set(config._default_values)
        loaded_sections = set(config.config.sections())

        # All of the defaults sections are in the loaded config
        self.assertTrue(set(default_sections).issubset(loaded_sections))

        # The test sections and values from each config are loaded
        self.assertEqual(config.config.get('section1', 'key1'), 'value1')
        self.assertEqual(config.config.get('section1', 'key2'), 'value2')
        self.assertEqual(config.config.get('section2', 'key1'), 'value3')

        # A new value is added to an existing section
        self.assertEqual(config.config.get('server', 'test_key'), 'test_value')

        # Existing values are overridden in an existing section
        self.assertEqual(config.config.get('server', 'server_name'), 'foo')

    def test_set_before_load(self):
        # Setting a config key triggers the lazy open
        self.assertFalse(config.config._loaded)
        config.config.set('section1', 'key', 'value')
        self.assertTrue(config.config._loaded)

        # All of the defaults sections are in the loaded config,
        # even when the .set call is what triggered the load
        self.assertTrue(set(config._default_values).issubset(config.config.sections()))

    def test_file_missing(self):
        missing = '/idontexist'
        config._config_files = [missing]

        with self.assertRaises(RuntimeError) as cm:
            config.config.sections()
        self.assertEqual(cm.exception.args[0],
                         'Cannot find configuration file: {0}'.format(missing))

    def test_file_read_denied(self):
        r_denied = self.config_1_name
        os.chmod(self.config_1_name, 0o0000)
        config._config_files = [r_denied]

        with self.assertRaises(RuntimeError) as cm:
            config.config.sections()
        self.assertEqual(cm.exception.args[0],
                         'Cannot read configuration file: {0}'.format(r_denied))

    def test_file_add_remove(self):
        self.assertIn(self.config_1_name, config._config_files)
        self.assertIn(self.config_2_name, config._config_files)
        self.assertIn('section1', config.config.sections())
        self.assertIn('section2', config.config.sections())

        # remove a config, make sure the other one's still loaded
        config.remove_config_file(self.config_2_name)
        self.assertIn('section1', config.config.sections())
        self.assertNotIn('section2', config.config.sections())

        # remove both, make sure neither is loaded
        config.remove_config_file(self.config_1_name)
        self.assertNotIn('section1', config.config.sections())
        self.assertNotIn('section2', config.config.sections())

        # add a config back, make sure the other still isn't loaded
        config.add_config_file(self.config_1_name)
        self.assertIn('section1', config.config.sections())
        self.assertNotIn('section2', config.config.sections())

        # add the other config back, everything should be loaded again
        config.add_config_file(self.config_2_name)
        self.assertIn('section1', config.config.sections())
        self.assertIn('section2', config.config.sections())

    def test_file_add_remove_existing(self):
        self.assertIn(self.config_1_name, config._config_files)

        # add a file that's already in the config files list
        with self.assertRaises(RuntimeError) as cm:
            config.add_config_file(self.config_1_name)
        self.assertIn(self.config_1_name, cm.exception.args[0])
        self.assertIn('already in configuration files', cm.exception.args[0])

        # remove a file that isn't in the config files list
        config.remove_config_file(self.config_1_name)
        self.assertNotIn(self.config_1_name, config._config_files)

        with self.assertRaises(RuntimeError) as cm:
            config.remove_config_file(self.config_1_name)
        self.assertIn(self.config_1_name, cm.exception.args[0])
        self.assertIn('not in configuration files', cm.exception.args[0])
