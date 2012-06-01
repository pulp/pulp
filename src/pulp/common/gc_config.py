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
cfg = Config(f)
validator = Validator(SCHEMA)
validator.validate(cfg)
"""

import re
import collections
from threading import RLock
from iniparse import INIConfig

# Contants

REQUIRED = 1
OPTIONAL = 0
ANY = None
NUMBER = '^\d+$'
BOOL = '(^YES$|^TRUE$|^1$|^NO$|^FALSE$|^0$)', re.I

#
# Utility
#

def getbool(value, default=False):
    """
    Get an INI property value as a python boolean.
    @param value: An INI property value.
    @type value: (str)
    @param default: The default value.
    @type default: bool
    @return: True if matches (true) pattern.
    @rtype: bool
    """
    if isinstance(value, str):
        return value.upper() in ('YES','TRUE','1')
    else:
        return default

#
# Validation
#

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
        PropertyException.__init__(self, name)
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
        @type cfg: Config
        @raise ValidationException: Or failed.
        @return: Two list: undefined sections and properties.
        @rtype: tuple
        """
        for section in self.schema:
            s = Section(section)
            section = cfg.get(s.name)
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
        if section is None:
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
            property = section.get(p.name)
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
        if value is None:
            if self.required:
                raise PropertyNotFound(self.name)
            return
        if not self.pattern:
            return
        p = Patterns.get(self.pattern)
        match = p.match(value)
        if not match:
            raise PropertyNotValid(self.name, value, self.pattern)

#
# Configuration
#
# Examples:
#
# note: Config "is a" dict so in the following examples,
#       cfg can be treated/passed as a dict or the value-add methods
#       can be used as appropriate.
#
# Loading a single .conf file.
# >>>
# >>> cfg = Config(path)
# >>>
#
# Loading and merging 2 .conf files.
# >>>
# >>> cfg = Config(path1, path2)
# >>>
# Same as:
# >>> cfg1 = Config(path1)
# >>> cfg2 = Config(path2)
# >>> cfg1.update(cfg2)
# >>>
#
# Load sections beginning with the name "foo-" using regex.
# >>>
# >>> cfg = Config(path1, path2, 'foo-')
# >>>
#
# Load sections 'server' & 'logging'
# >>>
# >>> cfg = Config(path1, path2, ['server', 'logging'])
# >>>


class Config(dict):
    """
    A dictionary constructed of INI files.
    The president is defined by the input ordering.  Each file loaded
    is merged into the dict in the order loaded.
    """

    def __init__(self, *inputs, **options):
        """
        @param input: A path or list of paths to .conf files
        @type input: str|dict|fp
        @param options: Options see: keywords
        @type filter: dict
        @keyword filter: A section filtering object.
            One of:
              - None: match ALL.
              - str : compiled as regex.
              - list: A list of strings to match.
              - tuple: A tuple of strings to match.
              - set: A set of strings to match.
              - callable: A funciton used to match.  Called as: filter(s).
        """
        filter = options.get('filter')
        for input in inputs:
            if isinstance(input, basestring):
                self.open(paths, filter)
                continue
            if isinstance(input, dict):
                self.update(input)
                continue
            self.read(input, filter)

    def open(self, paths, filter=None):
        """
        @param paths: A path or list of paths to .conf files
        @type paths: str|list
        @param filter: A section filtering object.
            One of:
              - None: match ALL.
              - str : compiled as regex.
              - list: A list of strings to match.
              - tuple: A tuple of strings to match.
              - set: A set of strings to match.
              - callable: A funciton used to match.  Called as: filter(s).
        @type filter: object
        """
        if isinstance(paths, basestring):
            paths = (paths,)
        for path in paths:
            fp = open(path)
            try:
                self.read(fp, filter)
            finally:
                fp.close()

    def read(self, fp, filter=None):
        """
        Read and parse the fp.
        @param fp: An open file
        @type fp: file-like object.
        @param filter: A section filtering object.
            One of:
              - None: match ALL.
              - str : compiled as regex.
              - list: A list of strings to match.
              - tuple: A tuple of strings to match.
              - set: A set of strings to match.
              - callable: A funciton used to match.  Called as: filter(s).
        @type filter: object
        """
        cfg = INIConfig(fp)
        filter = Filter(filter)
        for s in cfg:
            if not filter.match(s):
                continue
            section = {}
            for p in cfg[s]:
                v = getattr(cfg[s], p)
                section[p] = v
            self[s] = section

    def update(self, other):
        """
        Deep update.
        @param other: Another dict.
        @type other: dict
        """
        for k,v in other.items():
            if k in self and isinstance(v, dict):
                self[k].update(v)
            else:
                self[k] = v

    def graph(self, strict=False):
        """
        Get an object representation of the dict (graph).
        Access using object attribute (.) dot notation.
        @param strict: Indicates that KeyError should be raised when
            undefined sections or properties are accessed.  When
            false, undefined sections are returned as empty dict and
            undefined properties are returned as (None).
        @type strict: bool
        @return: An object representation
        @rtype: cfg
        """
        return Graph(self, strict)
    
    def validate(self, schema):
        """
        Perform validation.
        @param schema: A schema object.
        @type schema: Schema
        @return: Two list: undefined sections and properties.
        @rtype: tuple
        @raise ValidationException: Not valid.
        """
        v = Validator(schema)
        return v.validate(self)

    def __setitem__(self, name, value):
        """
        Set a section value.
        @param name: A section name.
        @type name: str
        @param value: A section.
        @type value: dict
        """
        if isinstance(value, dict):
            dict.__setitem__(self, name, value)
        else:
            raise ValueError('must be <dict>')


class Filter:
    """
    Filter object used to wrap various types of objects
    that can be used to filter sections.
    @ivar filter: A filter object.  See: __init__()
    @type filter: object
    """

    def __init__(self, filter):
        """
        @param filter: A filter object.
            One of:
              - None: match ALL.
              - str : compiled as regex.
              - list: A list of strings to match.
              - tuple: A tuple of strings to match.
              - set: A set of strings to match.
              - callable: A funciton used to match.  Called as: filter(s).
        @type filter: object
        """
        self.filter = filter

    def match(self, s):
        """
        Match the specified string.
        Delegated to the contained (filter) based on type.  See: __init__().
        @param s: A string to match.
        @type s: str
        @return: True if matched.
        @rtype: bool
        """
        if self.filter is None:
            return True
        if isinstance(self.filter, str):
            p = Patterns.get(self.filter)
            return p.match(s)
        if hasattr(collections, "Iterable"):
            if isinstance(self.filter, collections.Iterable):
                return s in self.filter
        else:
            if hasattr(self.filter, "__iter__"):
                return s in self.filter
        if callable(self.filter):
            return self.filter(s)
        fclass = self.filter.__class__.__name__
        raise Exception('unsupported filter: %s', fclass)


class Graph:
    """
    An object graph representation of a Config.
    Provides access using object attribute (.) dot notation.
    @ivar __dict: The wrapped config.
    @type __dict: dict
    @ivar __strict: Indicates that KeyError should be raised when
        undefined sections are accessed.  When false, undefined 
        sections are returned as empty dict
    @type __strict: bool
    """

    def __init__(self, dict, strict=False):
        """
        @param dict: The wrapped config.
        @type dict: dict
        @param strict: Indicates that KeyError should be raised when
            undefined sections are accessed.  When false, undefined 
            sections are returned as empty dict.
        @type strict: bool
        """
        self.__dict = dict
        self.__strict = strict

    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            return getattr(self.__dict, name)
        if self.__strict:
            s = self[name]
        else:
            s = self.__dict.get(name, {})
        return GraphSection(s, self.__strict)


class GraphSection:
    """
    An object graph representation of a section.
    @ivar __dict: The wrapped section.
    @type __dict: dict
    @ivar __strict: Indicates that KeyError should be raised when
        undefined properties are accessed.  When false, undefined 
        properties are returned as (None).
    @type __strict: bool
    """

    def __init__(self, dict, strict=False):
        """
        @param dict: The wrapped section.
        @type dict: dict
        @param strict: Indicates that KeyError should be raised when
            undefined properties are accessed.  When false, undefined 
            properties are returned as (None).
        @type strict: bool
        """        
        self.__dict = dict
        self.__strict = strict

    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            return getattr(self.__dict, name)
        if self.__strict:
            return self.__dict[name]
        else:
            return self.__dict.get(name)
