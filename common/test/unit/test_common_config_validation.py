#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import re
from StringIO import StringIO
import unittest
from mock import patch

from pulp.common.config import *


SCHEMA = (
    ('server', REQUIRED,
        (
            ('name', REQUIRED, ANY),
            ('url', REQUIRED, 'http://.+'),
            ('port', REQUIRED, NUMBER),
        )
    ),
    ('limits', OPTIONAL,
        (
            ('threads', OPTIONAL, NUMBER),
            ('posix', OPTIONAL, BOOL),
            ('mode', REQUIRED, '(AUTO$|MANUAL$)'),
        )
    ),
)

VALID = """
[server]
url=http://foo.com
port=10
name=elvis

[limits]
threads=10
posix=true
mode=AUTO
"""

EXTRA_SECTIONS_AND_PROPERTIES = """
%s
cpu=10
color=blue

[wtf]
name=john
age=10
""" % VALID

OVERRIDE_PROPERTIES = """
[server]
url=http://bar.com
"""

MISSING_REQUIRED_SECTION = """
[limits]
threads=10
posix=true
mode=AUTO
"""

MISSING_OPTIONAL_SECTION = """
[server]
url=http://foo.com
port=10
name=elvis
"""

MISSING_REQUIRED_PROPERTY = """
[server]
url=http://foo.com
name=elvis

[limits]
threads=10
posix=true
mode=AUTO
"""

MISSING_OPTIONAL_PROPERTY = """
[server]
url=http://foo.com
port=10
name=elvis

[limits]
mode=AUTO
"""

TEST_MISSING_REQUIRED_VALUE = """
[server]
url=
port=10
name=elvis

[limits]
threads=10
posix=true
mode=AUTO
"""

TEST_MISSING_OPTIONAL_VALUE = """
[server]
url=http://foo.com
port=10
name=

[limits]
threads=10
posix=true
mode=AUTO
"""

TEST_INVALID_VALUE = """
[server]
url=http://foo.com
port=hello
name=elvis

[limits]
threads=10
posix=true
mode=AUTO
"""

RANDOM_1 = """
[abc]
name=joe
age=10
phone=555-1212
[abcdef]
foo=ABC
bar=DEF
[my_a]
color=blue
height=88
weight=7
[my_b]
width=99
length=44
wood=oak
"""

class TestConfigValidator(unittest.TestCase):

    def test_valid(self):
        validator = Validator(SCHEMA)
        for s in (VALID,
                  MISSING_OPTIONAL_SECTION,
                  MISSING_OPTIONAL_PROPERTY,
                  TEST_MISSING_OPTIONAL_VALUE,):
            cfg = self.read(s)
            validator.validate(cfg)

    def test_invalid(self):
        validator = Validator(SCHEMA)
        for s in (MISSING_REQUIRED_SECTION,
                  MISSING_REQUIRED_PROPERTY,
                  TEST_MISSING_REQUIRED_VALUE,
                  TEST_INVALID_VALUE,):
            cfg = self.read(s)
            self.assertRaises(ValidationException, validator.validate, cfg)

    def test_extras(self):
        cfg = self.read(EXTRA_SECTIONS_AND_PROPERTIES)
        s,p = cfg.validate(SCHEMA)
        self.assertEqual(len(s), 1)
        self.assertEqual(s, ['wtf'])
        self.assertEqual(sorted(p), sorted(['limits.cpu', 'limits.color']))

    def test_util(self):
        cfg = self.read(VALID).graph(True)
        # getbool()
        v = parse_bool(cfg.limits.posix)
        self.assertTrue(isinstance(v, bool))

    def test_section_filtering(self):
        # load using Config.read()
        self.__test_section_filtering(self.read)
        # load using Config.update()
        def fn(s, filter):
            fp = StringIO(s)
            d = dict(Config(fp))
            return Config(d, filter=filter)
        self.__test_section_filtering(fn)

    def __test_section_filtering(self, read):
        # (abc) only
        cfg = read(RANDOM_1, 'abc$')
        self.assertEquals(len(cfg), 1)
        self.assertTrue('abc' in cfg)
        # (abc*) only
        cfg = read(RANDOM_1, 'abc')
        self.assertEquals(len(cfg), 2)
        self.assertTrue('abc' in cfg)
        self.assertTrue('abcdef' in cfg)
        # (my_a|my_b) only
        cfg = read(RANDOM_1, 'my_a|my_b')
        self.assertEquals(len(cfg), 2)
        self.assertTrue('my_a' in cfg)
        self.assertTrue('my_b' in cfg)
        # list filter
        cfg = read(RANDOM_1, ['abcdef'])
        self.assertEquals(len(cfg), 1)
        self.assertTrue('abcdef' in cfg)
        # tuple filter
        cfg = read(RANDOM_1, ('abcdef','my_b'))
        self.assertEquals(len(cfg), 2)
        self.assertTrue('abcdef' in cfg)
        self.assertTrue('my_b' in cfg)
        # callable filter
        def fn(s):
            return s in ('my_a', 'my_b')
        cfg = read(RANDOM_1, fn)
        self.assertEquals(len(cfg), 2)
        self.assertTrue('my_a' in cfg)
        self.assertTrue('my_b' in cfg)
        # (my_a|my_b) only with regex
        cfg = read(RANDOM_1, 'my_')
        self.assertEquals(len(cfg), 2)
        self.assertTrue('my_a' in cfg)
        self.assertTrue('my_b' in cfg)
        # (my_a|my_b) only with regex pattern passed as callable
        pattern = re.compile('my_')
        cfg = read(RANDOM_1, pattern.match)
        self.assertEquals(len(cfg), 2)
        self.assertTrue('my_a' in cfg)
        self.assertTrue('my_b' in cfg)

    def test_graph(self):
        cfg = self.read(VALID).graph()
        v = cfg.server.port
        self.assertEquals(v, '10')
        v = cfg.xxx.port
        self.assertEquals(v, None)
        v = cfg.server.xxx
        self.assertEquals(v, None)
        v = cfg.xxx
        self.assertEquals(v, {})

    def test_override(self):
        # Setup
        valid_fp = StringIO(VALID)
        override_fp = StringIO(OVERRIDE_PROPERTIES)

        config = Config(valid_fp, override_fp)

        # Test
        value = config['server']['url']

        # Verify
        self.assertEqual(value, 'http://bar.com')

    def test_has_option(self):
        # Setup
        config = self.read(VALID)

        # Test
        self.assertTrue(config.has_option('server', 'url'))
        self.assertTrue(not config.has_option('server', 'foo'))
        self.assertTrue(not config.has_option('bar', 'foo'))

    def read(self, s, filter=None):
        fp = StringIO(s)
        cfg = Config(fp, filter=filter)
        return cfg


class TestReadJsonConfig(unittest.TestCase):
    """
    Class to package up all the tests for the generic code to read
    json configurations from a file
    """

    @patch('os.path.exists', autospec=True)
    @patch('__builtin__.open', autospec=True)
    def test_read_json_config(self, mock_open, exists):
        exists.return_value = True
        mock_open.return_value.read.return_value = '{"foo":"bar"}'

        config = read_json_config("server/foo")
        mock_open.assert_called_once_with('/etc/pulp/server/foo', 'r')

        self.assertEqual(config, {'foo': 'bar'})


    @patch('os.path.exists', autospec=True)
    @patch('__builtin__.open', autospec=True)
    def test_read_json_config_prepended_slash_in_path(self, mock_open, exists):
        exists.return_value = True
        mock_open.return_value.read.return_value = '{"foo":"bar"}'
        read_json_config("/server/foo")
        mock_open.assert_called_once_with('/etc/pulp/server/foo', 'r')

    def test_read_json_config_non_existent_file(self):
        config = read_json_config("bad/file/name")
        self.assertEqual(config, {})



