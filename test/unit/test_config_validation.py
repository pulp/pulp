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

# Python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from StringIO import StringIO
from iniparse import INIConfig
from pulp.common.config import *
from pulp.client.admin.config import AdminConfig
from pulp.client.consumer.config import ConsumerConfig


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

class TestConfigValidator(testutil.PulpAsyncTest):

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
        validator = Validator(SCHEMA)
        cfg = self.read(EXTRA_SECTIONS_AND_PROPERTIES)
        s,p = validator.validate(cfg)
        self.assertEqual(len(s), 1)
        self.assertEqual(s, ['wtf'])
        self.assertEqual(p, ['limits.cpu', 'limits.color'])

    def test_admin(self):
        AdminConfig()

    def test_consumer(self):
        ConsumerConfig()

    def test_util(self):
        cfg = self.read(VALID)
        # nvl()
        v = nvl(cfg.limits.max, 99)
        self.assertEqual(v, 99)
        v = nvl(cfg.limits.threads, 99)
        self.assertEqual(v, '10')
        # getbool()
        v = getbool(cfg.limits.posix)
        self.assertTrue(isinstance(v, bool))
        v = getbool(cfg.limits.foo)
        self.assertTrue(isinstance(v, bool))

    def read(self, s):
        return INIConfig(StringIO(s))
