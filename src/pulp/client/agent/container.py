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
from pulp.client.agent.handler import Handler
from logging import getLogger

log = getLogger(__name__)


class Descriptor:
    """
    Content handler descriptor and configuration.
    @cvar ROOT: The default directory contining descriptors.
    @type ROOT: str
    @ivar name: The content unit name
    @type name: str
    @ivar cfg: The raw INI configuration object.
    @type cfg: INIConfig
    """
    
    ROOT = '/etc/pulp/handler'

    SCHEMA = (
        ('main', REQUIRED,
            (
                ('enabled', REQUIRED, BOOL),
                ('types', REQUIRED, ANY),
            ),
        ),
    )

    @classmethod
    def list(cls, root=ROOT):
        """
        Load the handler descriptors.
        @param root: The root directory contining descriptors.
        @type root: str
        @return: A list of descriptors.
        @rtype: list
        """
        descriptors = []
        cls.__mkdir(root)
        for name, path in cls.__list(root):
            try:
                descriptor = cls(name, path)
                if not descriptor.enabled():
                    continue
                descriptors.append((name, descriptor))
            except:
                log.exception(path)
        return descriptors

    @classmethod
    def __list(cls, root):
        """
        Load the handler descriptors.
        @param root: The root directory contining descriptors.
        @type root: str
        @return: A list of descriptors.
        @rtype: list
        """
        files = os.listdir(root)
        for fn in sorted(files):
            part = fn.split('.', 1)
            if len(part) < 2:
                continue
            name,ext = part
            if not ext in ('.conf'):
                continue
            path = os.path.join(root, fn)
            if os.path.isdir(path):
                continue
            yield (name, path)

    @classmethod
    def __mkdir(cls, path):
        """
        Ensure the descriptor root directory exists.
        @param path: The root directory contining descriptors.
        @type path: str
        """
        if not os.path.exists(path):
            os.makedirs(path)

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
        cfg = self.slice(cfg, section)
        validator = Validator(schema)
        validator.validate(cfg)
        self.cfg = self.dict(cfg, section)

    def slice(self, cfg, section):
        """
        Construct an INIConfig object containing only the specified sections.
        @param cfg: The handler descriptor configuration.
        @type cfg: INIConfig
        @param section: A section name to slice.
        @type section: str
        @return: A configuration object containing only the
            specfified section.
        @rtype: INIConfig
        """
        slice = INIConfig()
        source = cfg[section]
        target = getattr(slice, section)
        for p in source:
            v = source[p]
            setattr(target, p, v)
        return slice
    
    def dict(self, cfg, section):
        """
        Get dict of typedef configuration.
        @param cfg: The handler descriptor configuration.
        @type cfg: INIConfig
        @return: A dict representation of the configuration.
        @rtype: dict
        """
        d = {}
        section = cfg[section]
        for p in section:
            v = section[p]
            d[p] = v
        return d

class Container:
    """
    A content handler container.
    Loads and maintains a collection of content handlers
    mapped by type_id.
    @cvar PATH: A list of directories containing handlers.
    @type PATH: list
    @ivar root: The descriptor root directory.
    @type root: str
    @ivar path: The list of directories to search for handlers.
    @type path: list
    """

    PATH = [
        '/usr/lib/pulp/handler',
        '/usr/lib64/pulp/handler',
        '/opt/pulp/handler',
    ]

    def __init__(self, root=Descriptor.ROOT, path=PATH):
        """
        @param root: The descriptor root directory.
        @type root: str
        @param path: The list of directories to search for handlers.
        @type path: list
        """
        self.root = root
        self.path = path
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
        for name, descriptor in Descriptor.list(self.root):
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
        return self.handlers.get(type_id)

    def all(self):
        """
        All handlers.
        @return: A list of handlers.
        @rtype: list
        """
        return self.handlers.values()

    def __import(self, name, descriptor):
        """
        Import the handler defined by the name and descriptor.
        @param name: The handler name.
        @type name: str
        @param descriptor: A handler descriptor.
        @type descriptor: L{Descriptor}
        """
        try:
            path = self.__findimpl(name)
            mangled = self.__mangled(name)
            mod = imp.load_source(mangled, path)
            for type_id in descriptor.types():
                typedef = Typedef(descriptor.cfg, type_id)
                hclass = typedef.cfg['class']
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
        for root in self.path:
            path = os.path.join(root, mod)
            if os.path.exists(path):
                log.info('using: %s', path)
                return path
        raise Exception('%s, not found in:%s' % (mod, self.path))