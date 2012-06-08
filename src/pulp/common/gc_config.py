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
Wrapper for all configuration access in Pulp, including server, client,
and agent handlers.

The entry point into this module is the Config class. It accepts one or more
files to load and after instantiation will be used to access the values within.

Example usage:
  config = Config('base.conf', 'override.conf')

The loaded sections can be filtered by passing in a keyword argument containing
a list of section names. For example, to only load the "main" and "server"
sections found in the configurations:

  config = Config('base.conf', filter=['main', 'server'])

The Config object also supports validation of the loaded configuration values.
The schema is defined in a nested tuple structure that defines each section
(along with its required/optional flag) and each property witin the section.
For each property, its required/optional flag and validation criteria are
specified. Criteria can take the form of one of the constants in this module
or a regular expression.

Example code for defining a schema and validating a config against it:

schema = (
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
            ('property3', REQUIRED, BOOL),
        ),
    ),
)

cfg = Config('base.conf')
cfg.validate(schema)
"""

import re
import collections
from threading import RLock
from iniparse import INIConfig

# -- constants ----------------------------------------------------------------

# Schema Constants
REQUIRED = 1
OPTIONAL = 0
ANY = None
NUMBER = '^\d+$'
BOOL = '(^YES$|^TRUE$|^1$|^NO$|^FALSE$|^0$)', re.I

# Regular expression to test if a value is a valid boolean type
BOOL_RE = re.compile(*BOOL)

# -- exceptions ---------------------------------------------------------------

class ValidationException(Exception):

    def __init__(self, name):
        super(ValidationException, self).__init__()

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

class Unparsable(Exception):
    """
    Raised if a value cannot be parsed into the requested type. For instance,
    attempting to parse a boolean out of text that does not match the supported
    ways of specifying a boolean.
    """
    pass

# -- public -------------------------------------------------------------------

def parse_bool(value):
    """
    Parses the given value into its boolean representation.
    @param value: value to test
    @type value: str
    @return: true or false depending on what is parsed
    @rtype: bool
    @raise Unparsable: if the value is not one of the accepted values for
           indicating a boolean
    """

    # Make sure the user correctly indicated a boolean value
    if not BOOL_RE.match(value):
        raise Unparsable()

    return value.upper() in ('YES','TRUE','1')

class Config(dict):
    """
    Holds configuration files in the INI format; all properties are in a
    named section and are accessed by specifying both the section name and
    the property name.

    Properties are accessed through a nested dictionary syntax where the first
    item is the section name and the second is the property name. For example,
    to access a property named "server" in section "[main]":

       value = config['main']['server']

    Alternatively, a dot notation syntax can be used by first retrieving a
    wrapper on top of the configuration through the graph() method:

       graph = config.graph()
       value = graph.main.server
    """

    def __init__(self, *inputs, **options):
        """
        Creates a blank configuration and loads one or more files or existing
        data.

        Values to the inputs parameter can be one of three things:
         - the full path to a file to load (str)
         - file object to read from
         - dictionary whose values will be merged into this instance

        The only valid key to options is the "filter" keyword. It is used to
        selectively load only certain sections from the specified files. Its
        value can be one of the following:
         - None: match all sections
         - str : compiled into a regular expression to match against section names
         - list/tuple/set: a list of section names to match
         - callable: a funciton used to determine acceptance; it must accept
           a single parameter which is the section name being tested and return
           a boolean

        @param inputs: one or more files to load (see above)
        @param options: see above
        """
        super(Config, self).__init__()

        filter = options.get('filter')
        for input in inputs:
            if isinstance(input, basestring):
                self.open(input, filter)
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
        Copies sections and properties from "other" into this instance.

        @param other: values to copy into this instance
        @type other: dict
        """
        for k,v in other.items():
            if k in self and isinstance(v, dict):
                self[k].update(v)
            else:
                self[k] = v

    def graph(self, strict=False):
        """
        Get an object representation of this instance. The data is the same,
        however the returned object supports a dot notation for accessing
        values.

        @param strict: Indicates that KeyError should be raised when
            undefined sections or properties are accessed. When
            false, undefined sections are returned as empty dict and
            undefined properties are returned as (None).
        @type strict: bool
        @return: graph object representation of the configuration
        @rtype: Graph
        """
        return Graph(self, strict)

    def validate(self, schema):
        """
        Validates the values in the instance against the given schema.
        @param schema: nested tuples as described in the module docs
        @type schema: tuple
        @return: two list: undefined sections and properties.
        @rtype: tuple
        @raise ValidationException: if the configuration does not pass validation
        """
        v = Validator(schema)
        return v.validate(self)

    def parse_bool(self, value):
        """
        Shadow of the module-level parse_bool method for import convenience.

        @param value: value to test
        @type  value: str

        @return: boolean representation of the given string
        @rtype:  bool

        @raise Unparsable: if the value is not a valid boolean identifier
        """
        return parse_bool(value)

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

# -- private ------------------------------------------------------------------

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
        @return: compiled pattern
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
        return regex, flags

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
