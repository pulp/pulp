# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
SCHEMA = (
    ('section1', REQUIRED,
        (
            ('property1', REQUIRED, NUMBER),
             ('property2', REQUIRED, 'http://.+'),
             ('property3', REQUIRED, ANY),
        ),
    ),
    ('section2', OPTIONAL,
        (
            ('property1', OPTIONAL, NUMBER),
             ('property2', OPTIONAL, BOOL),
             ('property3', REQUIRED, BOOL,re.I),
        ),
    ),
)

f = open('my.conf')
cfg = INIConfig(f)
validator = Validator(SCHEMA)
validator.validate(cfg)
"""

import re
from threading import RLock
from iniparse.config import Undefined

# Contants

REQUIRED = 1
OPTIONAL = 0
ANY = None
NUMBER = '^\d+$'
BOOL = '(^YES$|^TRUE$|^1$|^NO$|^FALSE$|^0$)', re.I

# Utility

def ndef(x):
    """
    Not defined.
    Named after #ifndef macro in C preprocessor.
    @param x: A section|property
    @type x: section|property
    @return: True if not defined.
    @rtype: bool
    """
    return isinstance(x, Undefined)

def nvl(x, default=None):
    """
    Decode null (not defined) values.
    Named after Oracle NVL() function.
    @param x: A section|property
    @type x: section|property
    @return: default when not defined, else x.
    """
    if ndef(x):
        return default
    else:
        return x

def getbool(value, default=False):
    """
    Get an INI property value as a python boolean.
    @param value: An INI property value.
    @type value: (str|Undefined)
    @param default: The default value.
    @type default: bool
    @return: True if matches (true) pattern.
    @rtype: bool
    """
    if isinstance(value, str):
        return value.upper() in ('YES','TRUE','1')
    else:
        return default
    
def getsection(cfg, name):
    """
    Safely get a section by name.
    Used for python < 2.7 compat.
    @param cfg: An config object.
    @type cfg: INIConfig
    @param name: A section name.
    @type name: str
    @return: The section.
    @rtype: ini.Section
    """
    try:
        return cfg[name]
    except KeyError:
        return Undefined(name, None)
    
def getproperty(section, name):
    """
    Safely get a property value by name.
    Used for python < 2.7 compat.
    @param section: An section object.
    @type section: ini.Section
    @param name: A property name.
    @type name: str
    @return: The property value.
    @rtype: any
    """
    try:
        return section[name]
    except KeyError:
        return Undefined(None, name)

# Validation

class ValidationException(Exception):

    def __init__(self, name):
        self.name = name
        self.path = ''

    def msg(self, fmt, *args):
        msg = fmt % args
        if self.path:
            msg = '%s in: %s' % (msg, self.path)
        return msg

class SectionNotFound(ValidationException):

    def __str__(self):
        return self.msg(
            'Required section [%s], not found',
            self.name)


class PropertyException(ValidationException):
    pass


class PropertyNotFound(PropertyException):

    def __str__(self):
        return self.msg(
            'Required property "%s", not found',
            self.name)


class PropertyNotValid(PropertyException):

    def __init__(self, name, value, pattern):
        self.name = name
        self.value = value
        self.pattern = pattern

    def __str__(self):
        return self.msg(
            'Property: %s value "%s" must be: %s',
            self.name,
            self.value,
            self.pattern)


class Validator:
    """
    The main validation object.
    @ivar schema: An INI schema.
    @type schema: Schema
    """

    def __init__(self, schema):
        """
        @param schema: An INI schema.
        @type schema: Schema
        """
        self.schema = schema

    def validate(self, cfg):
        """
        Validate the specified INI configuration object.
        @param cfg: An INI configuration object.
        @type cfg: INIConfig
        @raise ValidationException: Or failed.
        @return: Two list: undefined sections and properties.
        @rtype: tuple
        """
        for section in self.schema:
            s = Section(section)
            section = getsection(cfg, s.name)
            s.validate(section)
        return self.undefined(cfg)

    def undefined(self, cfg):
        """
        Report section and properties found in the configuration
        that are not defined in the schema.
        @param cfg: An INI configuration object.
        @type cfg: INIConfig
        @return: Two lists: sections, properties
        @rtype: tuple
        """
        extras = ([],[])
        expected = {}
        for section in [s for s in self.schema]:
            properties = set()
            expected[section[0]] = properties
            for pn in section[2]:
               properties.add(pn[0])
        for sn in cfg:
            session = expected.get(sn)
            if not session:
                extras[0].append(sn)
                continue
            for pn in cfg[sn]:
                if pn not in session:
                    pn = '.'.join((sn,pn))
                    extras[1].append(pn)
        return extras



class Patterns:
    """
    Regex pattern cache object.
    Used so we don't compile regular expressions one than once.
    @cvar patterns: The dictionary of compiled patterns.
    @type patterns: dict
    """

    patterns = {}
    __mutex = RLock()

    @classmethod
    def get(cls, regex):
        """
        Get a compiled pattern.
        @param regex: A regular expression.
        @type regex: str|(str,int)
        @return: A compiled pattern.
        @rtype: Pattern
        """
        key = regex
        regex, flags = cls.split(regex)
        cls.__lock()
        try:
            p = cls.patterns.get(regex)
            if p is None:
                p = re.compile(regex, flags)
                cls.patterns[key] = p
            return p
        finally:
            cls.__unlock()

    @classmethod
    def split(cls, x):
        if isinstance(x, tuple):
            regex = x[0]
            flags = x[1]
        else:
            regex = x
            flags = 0
        return (regex,flags)

    @classmethod
    def __lock(cls):
        cls.__mutex.acquire()

    @classmethod
    def __unlock(cls):
        cls.__mutex.release()


class Section:
    """
    A section validation object.
    Used to validate INI sections based on schema.
    @ivar name: The section name.
    @type name: str
    @ivar required: Indicates the section is required.
    @type required: bool
    @ivar properties: List of property specifications.
    @type properties: list
    """

    def __init__(self, section):
        """
        @param section: The section schema specification.
            specification: (name, required, properties)
        @type section: tuple
        """
        self.name = section[0]
        self.required = section[1]
        self.properties = section[2]

    def validate(self, section):
        """
        Validate a configuration section object.
        Also validates properties.
        @param section: An INI section object.
        @type section: iniparse.ini.INISection
        @raise SectionException: On failure.
        """
        if ndef(section):
            if self.required:
                raise SectionNotFound(self.name)
        else:
            for property in self.properties:
                self.validproperty(section, property)

    def validproperty(self, section, property):
        """
        Validate a property specification.
        @param section: An INI section object.
        @type section: iniparse.ini.INISection
        @param property: A property specification.
            format: (name, required, pattern)
        @type property: tuple
        @raise SectionException: On failure.
        """
        p = Property(property)
        try:
            property = getproperty(section, p.name)
            p.validate(property)
        except PropertyException, pe:
            pe.name = '.'.join((self.name, pe.name))
            raise pe


class Property:
    """
    A property validation object.
    Used to validate INI sections property objects based on schema.
    @ivar name: The property name.
    @type name: str
    @ivar required: Indicates the property is required.
    @type required: bool
    @ivar pattern: A regex used to validate the property
        value.  A (None) pattern indicates no value validation.
    @type pattern: str
    """

    def __init__(self, property):
        """
        @param property: A property schema specification.
            format: (name, required, pattern)
        @type property: tuple
        """
        self.name = property[0]
        self.required = property[1]
        self.pattern = property[2]

    def validate(self, value):
        """
        Validate a configuration section object.
        Also validates properties.
        @param value: An property value.
        @type value: str
        @raise PropertyException: On failure.
        """
        if ndef(value):
            if self.required:
                raise PropertyNotFound(self.name)
            return
        if not self.pattern:
            return
        p = Patterns.get(self.pattern)
        match = p.match(value)
        if not match:
            raise PropertyNotValid(self.name, value, self.pattern)
