# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
Loader module that provides the infratructure and api for loading generic
content plugins and type definitions.
"""

import copy
import logging
import os
import re
import sys
from gettext import gettext as _
from pprint import pformat

try:
    import json
except ImportError:
    import simplejson as json

from pulp.server.content.plugins.distributor import Distributor
from pulp.server.content.plugins.importer import Importer
from pulp.server.content.types import database, parser
from pulp.server.content.types.model import TypeDescriptor
from pulp.server.pexceptions import PulpException

# constants --------------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# implicit singleton instance of PluginLoader

_LOADER = None

# plugin locations

_PLUGINS_ROOT = '/var/lib/pulp/plugins'
_DISTRIBUTORS_DIR = _PLUGINS_ROOT + '/distributors'
_IMPORTERS_DIR = _PLUGINS_ROOT + '/importers'
_PROFILERS_DIR = _PLUGINS_ROOT + '/profilers'
_TYPES_DIR = _PLUGINS_ROOT + '/types'

# plugin loading

_CONFIG_REGEX = re.compile('.*\.(config|conf|cfg)$', re.IGNORECASE)
_INIT_REGEX = re.compile('__init__.py(c|o)?$')

# exceptions -------------------------------------------------------------------

class PluginLoaderException(PulpException):
    """
    Base plugin loader exception.
    """
    pass


class PluginLoadError(PluginLoaderException):
    """
    Raised when error are encounterd while loading plugins.
    """
    pass

# derivative classes used for testing
class InvalidImporter(PluginLoadError): pass
class MalformedMetadata(PluginLoadError): pass
class MissingMetadata(PluginLoadError): pass
class MissingPluginClass(PluginLoadError): pass
class MissingPluginModule(PluginLoadError): pass
class MissingPluginPackage(PluginLoadError): pass


class ConflictingPluginError(PluginLoaderException):
    """
    Raised when 2 or more plugins try to handle the same content, distribution,
    or progile type(s).
    """
    pass

# derivative classes used for testing
class ConflictingPluginName(ConflictingPluginError): pass
class ConflictingPluginTypes(ConflictingPluginError): pass


class PluginNotFound(PluginLoaderException):
    """
    Raised when a plugin cannot be located.
    """
    pass

# loader public api methods ----------------------------------------------------

# state management

def initialize(validate=True):
    """
    Initialize the loader module by loading all type definitions and plugins.
    @param validate: if True, perform post-initialization validation
    @type validate: bool
    """
    global _LOADER
    # pre-ininitialzation validation
    assert not _is_initialized()
    _check_path(_PLUGINS_ROOT)
    # initialization
    _create_loader()
    _load_content_types(_TYPES_DIR)
    _LOADER.load_distributors_from_path(_DISTRIBUTORS_DIR)
    _LOADER.load_importers_from_path(_IMPORTERS_DIR)
    _LOADER.load_profilers_from_path(_PROFILERS_DIR)
    # post-initialization validation
    if not validate:
        return
    _validate_importers()


def finalize():
    """
    Finalize the loader module by freeing all of the plugins.
    """
    # NOTE this method isn't necessary for the pulp server
    # it is provided for testing purposes
    global _LOADER
    assert _is_initialized()
    _LOADER = None

# query api

def list_content_types():
    """
    List the supported content types.
    @return: list of content types
    @rtype: list
    """
    assert _is_initialized()
    return database.all_type_collection_names()


def list_distributors():
    """
    List the loaded distributors.
    @return: list of distributor names
    @rtype: list
    """
    assert _is_initialized()
    return sorted(_LOADER.get_loaded_distributors().keys())


def list_importers():
    """
    List the loaded importers.
    @return: list of importer names
    @rtype: list
    """
    assert _is_initialized()
    return sorted(_LOADER.get_loaded_importers().keys())


def list_profilers():
    """
    List the loaded profilers.
    @return: list of profiler names
    @rtype: list
    """
    assert _is_initialized()
    return sorted(_LOADER.get_loaded_profilers().keys())


def list_distributor_types(name):
    """
    List the supported distribution types for the given distributor name.
    @param name: name of the distributor
    @type name: str
    @return: tuple of types supported by the distributor
    @rtype: tuple
    @raise: L{PluginNotFound} if no distributor corresponds to the name
    """
    assert _is_initialized()
    types = _LOADER.get_loaded_distributors().get(name, None)
    if types is None:
        raise PluginNotFound(_('No plugin found: %(n)s') % {'n': name})
    return types


def list_importer_types(name):
    """
    List the supported content types for the given importer name.
    @param name: name of the importer
    @type name: str
    @return: tuple of types supported by the importer
    @rtype: tuple
    @raise: L{PluginNotFound} if no importer corresponds to the name
    """
    assert _is_initialized()
    types = _LOADER.get_loaded_importers().get(name, None)
    if types is None:
        raise PluginNotFound(_('No plugin found: %(n)s') % {'n': name})
    return types


def list_profiler_types(name):
    """
    List the supported profile types for the given profiler name.
    @param name: name of the profiler
    @type name: str
    @return: tuple of types supported by the profiler
    @rtype: tuple
    @raise: L{PluginNotFound} if no profiler corresponds to the name
    """
    assert _is_initialized()
    types = _LOADER.get_loaded_profilers().get(name, None)
    if types is None:
        raise PluginNotFound(_('No plugin found: %(n)s') % {'n': name})
    return types


def is_valid_distributor(name):
    """
    Check to see that a distributor exists for the given name.
    @param name: name of the distributor
    @type name: str
    @return: True if the distributor exists, False otherwise
    @rtype: bool
    """
    assert _is_initialized()
    plugins = _LOADER.get_loaded_distributors()
    return name in plugins


def is_valid_importer(name):
    """
    Check to see that a importer exists for the given name.
    @param name: name of the importer
    @type name: str
    @return: True if the importer exists, False otherwise
    @rtype: bool
    """
    assert _is_initialized()
    plugins = _LOADER.get_loaded_importers()
    return name in plugins


def is_valid_profiler(name):
    """
    Check to see that a profiler exists for the given name.
    @param name: name of the profiler
    @type name: str
    @return: True if the profiler exists, False otherwise
    @rtype: bool
    """
    assert _is_initialized()
    plugins = _LOADER.get_loaded_profilers()
    return name in plugins

# plugin api

def get_distributor_by_name(name):
    """
    Get a distributor instance that corresponds to the given name.
    @param name: name of the distributor
    @type name: str
    @return: tuple of L{Distributor} instance and dictionary configuration
    @rtype: tuple (L{Distributor}, dict)
    @raise: L{PluginNotFound} if no distributor corresponds to the name
    """
    assert _is_initialized()
    cls, cfg = _LOADER.get_distributor_by_name(name)
    return (cls(), cfg)


def get_importer_by_name(name):
    """
    Get an importer instance that corresponds to the given name.
    @param name: name of the importer
    @type name: str
    @return: tuple of L{Importer} instance and dictionary configuration
    @rtype: tuple (L{Importer}, dict)
    @raise: L{PluginNotFound} if no importer corresponds to the name
    """
    assert _is_initialized()
    cls, cfg = _LOADER.get_importer_by_name(name)
    return (cls(), cfg)


def get_profiler_by_name(name):
    """
    Get a profiler instance that corresponds to the given name.
    @param name: name of the profiler
    @type name: str
    @return: tuple of L{Profiler} instance and dictionary configuration
    @rtype: tuple (L{Profiler}, dict)
    @raise: L{PluginNotFound} if no profiler corresponds to the name
    """
    assert _is_initialized()
    cls, cfg = _LOADER.get_profiler_by_name(name)
    return (cls(), cfg)

# loader class -----------------------------------------------------------------

class PluginLoader(object):
    """
    Class to load heterogeneous types of plugins and manage their class,
    configuration, and supported types associations.
    """

    def __init__(self):
        self.__distributors = _PluginMap()
        self.__importers = _PluginMap()
        self.__profilers = _PluginMap()

    # plugin management api

    def add_distributor(self, name, cls, cfg):
        """
        @param name: distributor name
        @type name: str
        @param cls: distributor class
        @type cls: type
        @param cfg: distributor configuration
        @type cfg: dict
        """
        types = _get_plugin_types(cls)
        self.__distributors.add_plugin(name, cls, cfg, types)

    def add_importer(self, name, cls, cfg):
        """
        @param name: importer name
        @type name: str
        @param cls: importer class
        @type cls: type
        @param cfg: importer configuration
        @type cfg: dict
        """
        types = _get_plugin_types(cls)
        self.__importers.add_plugin(name, cls, cfg, types)

    def add_profiler(self, name, cls, cfg):
        """
        @param name: profiler name
        @type name: str
        @param cls: profiler class
        @type cls: type
        @param cfg: profiler configuration
        @type cfg: dict
        """
        types = _get_plugin_types(cls)
        self.__profilers.add_plugin(name, cls, cfg, types)

    def load_distributors_from_path(self, path):
        """
        @param path: distributors root directory
        @type path: str
        """
        _check_path(path)
        _add_path_to_sys_path(path)
        _load_plugins_from_path(path, Distributor, self.__distributors)

    def load_importers_from_path(self, path):
        """
        @param path: importers root directory
        @type path: str
        """
        _check_path(path)
        _add_path_to_sys_path(path)
        _load_plugins_from_path(path, Importer, self.__importers)

    def load_profilers_from_path(self, path):
        """
        @param path: profilers root directory
        @type path: str
        """
        _check_path(path)
        _LOG.warn(_('Profilers load called, but not implemented'))

    def remove_distributor(self, name):
        """
        @param name: distributor name
        @type name: str
        """
        self.__distributors.remove_plugin(name)

    def remove_importer(self, name):
        """
        @param name: importer name
        @type name: str
        """
        self.__importers.remove_plugin(name)

    def remove_profiler(self, name):
        """
        @param name: profiler name
        @type name: str
        """
        self.__profilers.remove_plugin(name)

    # plugin lookup api

    def get_distributor_by_name(self, name):
        """
        @param name: distributor name
        @type name: str
        @return: tuple of distributor (class, configuration)
        @rtype: tuple (L{Distributor}, dict)
        """
        return self.__distributors.get_plugin_by_name(name)

    def get_distributor_by_type(self, distribution_type):
        """
        @param distribution_type: distribution type
        @type distribution_type: str
        @return: tuple of distributor (class, configuration)
        @rtype: tuple (L{Distributor}, dict)
        """
        return self.__distributors.get_plugin_by_type(distribution_type)

    def get_importer_by_name(self, name):
        """
        @param name: importer name
        @type name: str
        @return: tuple of importer (class, configuration)
        @rtype: tuple (L{Importer}, dict)
        """
        return self.__importers.get_plugin_by_name(name)

    def get_importer_by_type(self, content_type):
        """
        @param content_type: content type
        @type content_type: str
        @return: tuple of importer (class, configuration)
        @rtype: tuple (L{Importer}, dict)
        """
        return self.__importers.get_plugin_by_type(content_type)

    def get_profiler_by_name(self, name):
        """
        @param name: profiler name
        @type name: str
        @return: tuple of profiler (class, configuration)
        @rtype: tuple (L{Profiler}, dict)
        """
        return self.__profilers.get_plugin_by_name(name)

    def get_profiler_by_type(self, profile_type):
        """
        @param profile_type: profile type
        @type profile_type: str
        @return: tuple of profiler (class, configuration)
        @rtype: tuple (L{Profiler}, dict)
        """
        return self.__profilers.get_plugin_by_type(profile_type)

    # plugin query api

    def get_loaded_distributors(self):
        """
        @return: dictionary of distributor name: tuple of types
        @rtype: dict {str: tuple}
        """
        # return a copy to avoid persisting external changes
        return copy.copy(self.__distributors.types)

    def get_loaded_importers(self):
        """
        @return: dictionary of importer name: tuple of types
        @rtype: dict {str: tuple}
        """
        # return a copy to avoid persisting external changes
        return copy.copy(self.__importers.types)

    def get_loaded_profilers(self):
        """
        @return: dictionary of profiler name: tuple of types
        @rtype: dict {str: tuple}
        """
        # return a copy to avoid persisting external changes
        return copy.copy(self.__profilers.types)

# plugin management class

class _PluginMap(object):
    """
    Convience class for managing plugins of a homogeneous type.
    @ivar configs: dict of associated configurations
    @ivar plugins: dict of associated classes
    @ivar types: dict of supported types the plugins operate on
    """

    def __init__(self):
        self.configs = {}
        self.plugins = {}
        self.types = {}

    def _find_conclicting_types(self, new_types):
        """
        @type new_types: list
        @rtype: list
        """
        conflicts = []
        for name, types in self.types.items():
            for type_ in types:
                if type_ not in new_types:
                    continue
                conflicts.append((name, type_))
        return conflicts

    def add_plugin(self, name, cls, cfg, types=()):
        """
        @type name: str
        @type cls: type
        @type cfg: dict
        @type types: list or tuple
        """
        if not _is_enabled(cfg):
            _LOG.info(_('Skipping plugin %(p)s: not enabled') % {'p': name})
            return
        if self.has_plugin(name):
            msg = _('Plugin with same name already exists: %(n)s')
            raise ConflictingPluginName(msg % {'n': name})
        conflicts = self._find_conclicting_types(types)
        if conflicts:
            msg = _('Plugin %(n)s conflicts with the follwing plugins: %(c)s')
            c = '; '.join('name: %s, type: %s' % (n, t) for n, t in conflicts)
            raise ConflictingPluginTypes(msg % {'n': name, 'c': c})
        self.plugins[name] = cls
        self.configs[name] = cfg
        self.types[name] = tuple(types)
        _LOG.info(_('Loaded plugin %(p)s for types: %(t)s') %
                  {'p': name, 't': ','.join(types)})
        _LOG.debug('class: %s; config: %s' % (cls.__name__, pformat(cfg)))

    def get_plugin_by_name(self, name):
        """
        @type name: str
        @rtype: tuple (type, dict)
        @raises L{PluginNotFound}
        """
        if not self.has_plugin(name):
            raise PluginNotFound(_('No plugin found: %(n)s') % {'n': name})
        # return a deepcopy of the config to avoid persisting external changes
        return (self.plugins[name], copy.deepcopy(self.configs[name]))

    def get_plugin_by_type(self, type_):
        """
        @type type_: str
        @rtype: tuple (type, dict)
        @raises L{PluginNotFound}
        """
        for name, types in self.types.items():
            if type_ not in types:
                continue
            return self.get_plugin_by_name(name)
        raise PluginNotFound(_('No plugin found for: %(t)s') % {'t': type_})

    def has_plugin(self, name):
        """
        @type name: str
        @rtype: bool
        """
        return name in self.plugins

    def remove_plugin(self, name):
        """
        @type name: str
        """
        if not self.has_plugin(name):
            return
        self.plugins.pop(name)
        self.configs.pop(name)
        self.types.pop(name)

# utility methods --------------------------------------------------------------

# general utility

def _check_path(path):
    """
    @type path: str
    @raise: ValueError
    """
    if os.access(path, os.F_OK | os.R_OK):
        return
    raise ValueError(_('Path not found: %(p)s') % {'p': path})


def _read_content(file_name):
    """
    @type file_name: str
    @rtype: str
    """
    handle = open(file_name, 'r')
    contents = handle.read()
    handle.close()
    return contents

# initialization

def _create_loader():
    global _LOADER
    _LOADER = PluginLoader()


def _is_initialized():
    """
    @rtype: bool
    """
    return isinstance(_LOADER, PluginLoader)


def _load_content_types(types_dir):
    """
    @type types_dir: str
    """
    _check_path(types_dir)
    descriptors = _load_type_descriptors(types_dir)
    _load_type_definitions(descriptors)


def _load_type_definitions(descriptors):
    """
    @type descriptors: list [L{TypeDescriptor}, ...]
    """
    definitions = parser.parse(descriptors)
    database.update_database(definitions)


def _load_type_descriptors(path):
    """
    @type path: str
    @rtype: list [L{TypeDescriptor}, ...]
    """
    _LOG.debug('Loading type descriptors from: %s' % path)
    descriptors = []
    for file_name in os.listdir(path):
        full_file_name = os.path.join(path, file_name)
        content = _read_content(full_file_name)
        descriptor = TypeDescriptor(file_name, content)
        descriptors.append(descriptor)
    return descriptors


def _validate_importers():
    """
    @raise: L{PluginLoadError}
    """
    assert _is_initialized()
    supported_types = list_content_types()
    for plugin_name, plugin_types in _LOADER.get_loaded_importers().items():
        for type_ in plugin_types:
            if type_ in supported_types:
                continue
            msg = _('Importer %(i)s: not type definition found for %(t)s')
            raise InvalidImporter(msg % {'i': plugin_name, 't': type_})

# plugin loading

def _add_path_to_sys_path(path):
    """
    @type path: str
    """
    _LOG.debug('Adding path to sys.path: %s' % path)
    if path in sys.path:
        return
    sys.path.append(path)


def _get_plugin_dirs(plugin_root):
    """
    @type plugin_root: str
    @rtype: list [str, ...]
    """
    _LOG.debug('Looking for plugin dirs in plugin root: %s' % plugin_root)
    dirs = []
    for entry in os.listdir(plugin_root):
        plugin_dir = os.path.join(plugin_root, entry)
        if not os.path.isdir(plugin_dir):
            continue
        dirs.append(plugin_dir)
    return dirs


def _get_plugin_metadata_field(plugin_class, field, default=None):
    """
    @type plugin_class: type
    @type field: str
    @rtype: str
    """
    metadata = plugin_class.metadata()
    if not isinstance(metadata, dict):
        raise MalformedMetadata(_('%(p)s.metadata() did not return a dictionary') %
                                {'p': plugin_class.__name__})
    value = metadata.get(field, default)
    return value


def _get_plugin_types(plugin_class):
    """
    @type plugin_class: type
    @rtype: list [str, ...]
    @raise: L{PluginLoadError}
    """
    _LOG.debug('Getting types for plugin class: %s' % plugin_class.__name__)
    types = _get_plugin_metadata_field(plugin_class, 'types')
    if types is None:
        raise MissingMetadata(_('%(p)s does not define any types') %
                              {'p': plugin_class.__name__})
    if isinstance(types, basestring):
        types = [types]
    return types


def _import_module(name):
    """
    @type name: str
    @rtype: module
    """
    _LOG.debug('Importing plugin module: %s' % name)
    if name in sys.modules:
        sys.modules.pop(name)
    mod = __import__(name)
    for sub in name.split('.')[1:]:
        mod = getattr(mod, sub)
    return mod


def _is_enabled(cfg):
    """
    @type cfg: dict
    @rtype: bool
    """
    return cfg.get('enabled', True)


def _load_plugin(path, base_class, module_name):
    """
    @type path: str
    @type base_class: type
    @type module_name: str
    @rtype: tuple (type, dict)
    @raise: L{PluginLoadError}
    """
    _LOG.debug('Loading plugin: %s, %s, %s' %
               (path, base_class.__name__, module_name))
    init_found = False
    module_regex = re.compile('%s\.py(c|o)?$' % module_name)
    module_found = False
    package_name = os.path.split(path)[-1]
    config_path = None
    # grok through the directory looking for plugin module and config
    for entry in os.listdir(path):
        if _INIT_REGEX.match(entry):
            init_found = True
        elif module_regex.match(entry):
            module_found = True
        elif _CONFIG_REGEX.match(entry):
            config_path = os.path.join(path, entry)
    # if the plugin is not a package, error out
    if not init_found:
        msg = _('%(n)s plugin is not a package: no __init__.py found')
        raise MissingPluginPackage(msg % {'n': package_name})
    # if we can't find the module, error out
    if not module_found:
        msg = _('%(n)s plugin has no module: %(p)s.%(m)s')
        d = {'n': module_name.title(), 'p': package_name, 'm': module_name}
        raise MissingPluginModule(msg % d)
    # load and return the plugin class and configuration
    cls = _load_plugin_class('.'.join((package_name, module_name)), base_class)
    cfg = {}
    if config_path is not None:
        cfg = _load_plugin_config(config_path)
    return (cls, cfg)


def _load_plugin_config(config_file_name):
    """
    @type config_file_name: str
    @rtype: dict
    """
    _LOG.debug('Loading config file: %s' % config_file_name)
    contents = _read_content(config_file_name)
    cfg = json.loads(contents)
    return cfg


def _load_plugin_class(module_name, base_class):
    """
    @type module_name: str
    @type base_class: type
    @rtype: attr
    @raise: L{PluginLoadError}
    """
    _LOG.debug('Loading plugin class: %s, %s' %
               (module_name, base_class.__name__))
    module = _import_module(module_name)
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if not isinstance(attr, type):
            continue
        if not issubclass(attr, base_class):
            continue
        if attr is base_class:
            continue
        return attr
    msg = _('%(m)s modules did not contain a derived class of %(c)s')
    raise MissingPluginClass(msg % {'m': module_name, 'c': base_class.__name__})


def _load_plugins_from_path(path, base_class, plugin_map):
    """
    @type path: str
    @type base_class: type
    @type plugin_map: L{_PluginMap}
    """
    _LOG.debug('Loading multiple plugins: %s, %s' %
               (path, base_class.__name__))
    plugin_dirs = _get_plugin_dirs(path)
    for dir_ in plugin_dirs:
        cls, cfg = _load_plugin(dir_, base_class, base_class.__name__.lower())
        name = _get_plugin_metadata_field(cls, 'name', cls.__name__)
        types = _get_plugin_types(cls)
        plugin_map.add_plugin(name, cls, cfg, types)

