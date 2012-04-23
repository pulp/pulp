#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import imp
import os
from iniparse import INIConfig
from pulp.common.config import Validator, REQUIRED, BOOL, ANY
from logging import getLogger

log = getLogger(__name__)

#
# Handler descriptor:
#
# [main]
# enabled=(0|1)
# types=(type_id,)
#
# [<type_id>]
# class=<str>
# <other>
#

class Handler:
    """
    Content (type) handler.
    """

    def install(self, units, options):
        """
        Install content unit(s).
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        @param options: Unit install options.
        @type options: dict
        """
        pass

    def update(self, units, options):
        """
        Update content unit(s).
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        @param options: Unit update options.
        @type options: dict
        """
        pass

    def uninstall(self, units, options):
        """
        Uninstall content unit(s).
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        @param options: Unit uninstall options.
        @type options: dict
        """
        pass

    def profile(self):
        pass


class Descriptor:
    """
    Content handler descriptor and configuration.
    @ivar name: The content unit name
    @type name: str
    @ivar cfg: The raw INI configuration object.
    @type cfg: INIConfig
    """

    ROOT = '/etc/pulp/consumer/agent/handler'

    SCHEMA = (
        ('main', REQUIRED,
            (
                ('enabled', REQUIRED, BOOL),
                ('types', REQUIRED, ANY),
            ),
        ),
    )

    @classmethod
    def list(cls):
        """
        Load the handler descriptors.
        @return: A list of descriptors.
        @rtype: list
        """
        descriptors = []
        cls.__mkdir()
        for name, path in cls.__list():
            try:
                descriptor = cls(name, path)
                if not descriptor.enabled():
                    continue
                descriptors.append((name, descriptor))
            except:
                log.exception(path)
        return descriptors

    @classmethod
    def __list(cls):
        """
        Load the handler descriptors.
        @return: A list of descriptors.
        @rtype: list
        """
        files = os.listdir(cls.ROOT)
        for fn in sorted(files):
            part = fn.split('.', 1)
            if len(part) < 2:
                continue
            name,ext = part
            if not ext in ('.conf'):
                continue
            path = os.path.join(cls.ROOT, fn)
            if os.path.isdir(path):
                continue
            yield (name, path)

    @classmethod
    def __mkdir(cls):
        """
        Ensure the descriptor root directory exists.
        """
        if not os.path.exists(cls.ROOT):
            os.makedirs(cls.ROOT)

    def __init__(self, name, path):
        """
        @param name: The handler name.
        @type name: str
        @param path: The absolute path to the descriptor.
        @type path: str
        """
        cfg = INIConfig(open(path))
        validator = Validator(self.SCHEMA)
        validator.validate(cfg)
        self.name = name
        self.cfg = cfg

    def enabled(self):
        """
        Get whether the handler is enabled.
        @return: True if enabled.
        @rtype: bool
        """
        return self.cfg.main.enabled

    def types(self):
        """
        Get a list of supported content types.
        @return: A list of supported content type IDs.
        @rtype: list
        """
        types = []
        listed = self.cfg.main.types
        for t in listed.split(','):
            t = t.strip()
            if t:
                types.append(t)
        return types


class Typedef:
    """
    Represents a handler type definition.
    @ivar cfg: The type specific content handler configuration.
        This is basically the [section] defined in the descriptor.
    @type cfg: INIConfig
    """

    def __init__(self, cfg, section):
        """
        Construct the object and validate the configuration.
        @param cfg: The descriptor configuration.
        @type cfg: INIConfig
        @param section: The typedef section name within the descriptor.
        @type section: str
        """
        schema = (
            (section, REQUIRED,
                (
                    ('class', REQUIRED, ANY),
                ),
             ),)
        cfg = self.__cfg(cfg, section)
        validator = Validator(schema)
        validator.validate(cfg)
        self.cfg = cfg

    def __cfg(self, cfg, section):
        """
        Construct an INIConfig object containing only the specified section.
        @param cfg: The handler descriptor configuration.
        @type cfg: INIConfig
        @param section: The section name within the configuration.
        @type section: str
        @return: A configuration object containing only the
            specfified section.
        @rtype: INIConfig
        """
        slice = INIConfig()
        for s in cfg:
            if s != section:
                continue
            for p in cfg[s]:
                v = cfg[s][p]
                slice[s][p] = v
        return slice


class Container:
    """
    A content handler container.
    Loads and maintains a collection of content handlers
    mapped by type_id.
    @cvar PATH: A list of directories containing handlers.
    @type PATH: list
    """

    PATH = [
        '/usr/lib/pulp/agent/handler',
        '/usr/lib64/pulp/agent/handler',
        '/opt/pulp/agent/handler',
    ]

    def __init__(self):
        """
        """
        self.reset()

    def reset(self):
        """
        Reset (empty) the container.
        """
        self.handlers = {}

    def load(self):
        """
        Load and validate content handlers.
        """
        self.reset()
        for name, descriptor in Descriptor.list():
            self.__import(name, descriptor)

    def find(self, type_id):
        """
        Find and return a content handler for the specified
        content type ID.
        @param type_id: A content type ID.
        @type type_id: str
        @return: The content type handler registered to
            handle the specified type ID.
        @rtype: L{Handler}
        """
        return self.handlers[type_id]

    def __import(self, name, descriptor):
        try:
            path = self.__findimpl(name)
            mangled = self.__mangled(name)
            mod = imp.load_source(mangled, path)
            for type_id in descriptor.types():
                typedef = Typedef(descriptor.cfg, type_id)
                hclass = typedef.cfg[type_id]['class']
                hclass = getattr(mod, hclass)
                handler = hclass(typedef.cfg)
                self.handlers[type_id] = handler
        except Exception:
            log.exception('handler "%s", import failed', name)

    def __mangled(self, name):
        """
        Mangle the module name to prevent (python) name collisions.
        @param name: A module name.
        @type name: str
        @return: The mangled name.
        @rtype: str
        """
        n = hash(name)
        n = hex(n)[2:]
        return ''.join((name, n))

    def __findimpl(self, name):
        """
        Find a handler module.
        @param name: The handler name.
        @type name: str
        @return: The fully qualified path to the handler module.
        @rtype: str
        @raise Exception: When not found.
        """
        mod = '%s.py' % name
        for root in self.PATH:
            path = os.path.join(root, mod)
            if os.path.exists(path):
                log.info('using: %s', path)
                return path
        raise Exception('%s, not found in:%s' % (mod, self.PATH))