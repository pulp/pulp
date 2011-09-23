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


class ConflictingPluginError(PluginLoaderException):
    """
    Raised when 2 or more plugins try to handle the same content, distribution,
    or progile type(s).
    """
    pass


class PluginNotFound(PluginLoaderException):
    """
    Raised when a plugin cannot be located.
    """
    pass

# loader public api methods ----------------------------------------------------

# state management

def initialize():
    global _LOADER
    assert not _is_initialized()
    _check_path(_PLUGINS_ROOT)
    _create_loader()
    _load_content_types()
    _load_distributors()
    _load_importers()
    _load_profilers()
    _validatie_importers()


def finalize():
    # NOTE this method isn't necessary for the pulp server
    # it is provided for testing purposes
    global _LOADER
    assert _is_initialized()
    _LOADER = None

# query api

def list_content_types():
    assert _is_initialized()
    return database.all_type_collection_names()


def list_distributors():
    assert _is_initialized()
    return sorted(_LOADER.get_loaded_distributors().keys())


def list_importers():
    assert _is_initialized()
    return sorted(_LOADER.get_loaded_importers().keys())


def list_profilers():
    assert _is_initialized()
    return sorted(_LOADER.get_loaded_profilers().keys())


def list_distributor_types(name):
    assert _is_initialized()
    types = _LOADER.get_loaded_distributors().get(name, None)
    if types is None:
        raise PluginNotFound(_('No plugin found: %(n)s') % {'n': name})
    return types


def list_importer_types(name):
    assert _is_initialized()
    types = _LOADER.get_loaded_importers().get(name, None)
    if types is None:
        raise PluginNotFound(_('No plugin found: %(n)s') % {'n': name})
    return types


def list_profiler_types(name):
    assert _is_initialized()
    types = _LOADER.get_loaded_profilers().get(name, None)
    if types is None:
        raise PluginNotFound(_('No plugin found: %(n)s') % {'n': name})
    return types


def is_valid_distributor(name):
    assert _is_initialized()
    plugins = _LOADER.get_loaded_distributors()
    return name in plugins


def is_valid_importer(name):
    assert _is_initialized()
    plugins = _LOADER.get_loaded_importers()
    return name in plugins


def is_valid_profiler(name):
    assert _is_initialized()
    plugins = _LOADER.get_loaded_profilers()
    return name in plugins

# plugin api

def get_distributor_by_name(name):
    assert _is_initialized()
    cls, cfg = _LOADER.get_distributor_by_name(name)
    return (cls(), cfg)


def get_importer_by_name(name):
    assert _is_initialized()
    cls, cfg = _LOADER.get_importer_by_name(name)
    return (cls(), cfg)


def get_profiler_by_name(name):
    assert _is_initialized()
    cls, cfg = _LOADER.get_profiler_by_name(name)
    return (cls(), cfg)

# loader class -----------------------------------------------------------------

class PluginLoader(object):

    def __init__(self):
        self.__distributors = _PluginMap()
        self.__importers = _PluginMap()
        self.__profilers = _PluginMap()

    # plugin management api

    def add_distributor(self, name, cls, cfg):
        types = _get_plugin_types(cls)
        self.__distributors.add_plugin(name, cls, cfg, types)

    def add_importer(self, name, cls, cfg):
        types = _get_plugin_types(cls)
        self.__importers.add_plugin(name, cls, cfg, types)

    def add_profiler(self, name, cls, cfg):
        types = _get_plugin_types(cls)
        self.__profilers.add_plugin(name, cls, cfg, types)

    def load_distributors_from_path(self, path):
        _load_plugins_from_path(path, Distributor, self.__distributors)

    def load_importers_from_path(self, path):
        _load_plugins_from_path(path, Importer, self.__importers)

    def load_profilers_from_path(self, path):
        _LOG.warn(_('Profilers load called, but not implemented'))

    def remove_distributor(self, name):
        self.__distributors.remove_plugin(name)

    def remove_importer(self, name):
        self.__importers.remove_plugin(name)

    def remove_profiler(self, name):
        self.__profilers.remove_plugin(name)

    # plugin lookup api

    def get_distributor_by_name(self, name):
        return self.__distributors.get_plugin_by_name(name)

    def get_distributor_by_type(self, distribution_type):
        return self.__distributors.get_plugin_by_type(distribution_type)

    def get_importer_by_name(self, name):
        return self.__importers.get_plugin_by_name(name)

    def get_importer_by_type(self, content_type):
        return self.__importers.get_plugin_by_type(content_type)

    def get_profiler_by_name(self, name):
        return self.__profilers.get_plugin_by_name(name)

    def get_profiler_by_type(self, profile_type):
        return self.__profilers.get_plugin_by_type(profile_type)

    # plugin query api

    def get_loaded_distributors(self):
        return copy.deepcopy(self.__distributors.types)

    def get_loaded_importers(self):
        return copy.deepcopy(self.__importers.types)

    def get_loaded_profilers(self):
        return copy.deepcopy(self.__profilers.types)

# plugin management class

class _PluginMap(object):

    def __init__(self):
        self.configs = {}
        self.plugins = {}
        self.types = {}

    def _find_conclicting_types(self, new_types):
        conflicts = []
        for name, types in self.types.items():
            for type_ in types:
                if type_ not in new_types:
                    continue
                conflicts.append((name, type_))
        return conflicts

    def add_plugin(self, name, cls, cfg, types=()):
        if self.has_plugin(name):
            msg = _('Plugin with same name already exists: %(n)s')
            raise ConflictingPluginError(msg % {'n': name})
        conflicts = self._find_conclicting_types(types)
        if conflicts:
            msg = _('Plugin %(n)s conflicts with the follwing plugins: %(c)s')
            c = '; '.join('name: %s, type: %s' % (n, t) for n, t in conflicts)
            raise ConflictingPluginError(msg % {'n': name, 'c': c})
        self.plugins[name] = cls
        self.configs[name] = cfg
        self.types[name] = tuple(types)
        _LOG.info(_('Loaded plugin %(p)s for types: %(t)s') %
                  {'p': name, 't': ','.join(types)})
        _LOG.debug('class: %s\nconfig: %s' % (cls.__name__, pformat(cfg)))

    def get_plugin_by_name(self, name):
        if not self.has_plugin(name):
            raise PluginNotFound(_('No plugin found: %(n)s') % {'n': name})
        return (self.plugins[name], copy.deepcopy(self.configs[name]))

    def get_plugin_by_type(self, type_):
        for name, types in self.types.items():
            if type_ not in types:
                continue
            return self.get_plugin_by_name(name)
        raise PluginNotFound(_('No plugin found for: %(t)s') % {'t': type_})

    def has_plugin(self, name):
        return name in self.plugins

    def remove_plugin(self, name):
        if not self.has_plugin(name):
            return
        self.plugins.pop(name)
        self.configs.pop(name)
        self.types.pop(name)

# utility methods --------------------------------------------------------------

# general utility

def _check_path(path):
    if os.access(path, os.F_OK | os.R_OK):
        return
    raise ValueError(_('Path not found: %(p)s') % {'p': path})


def _read_content(file_name):
    handle = open(file_name, 'r')
    contents = handle.read()
    handle.close()
    return contents

# initialization

def _create_loader():
    global _LOADER
    _LOADER = PluginLoader()


def _is_initialized():
    return isinstance(_LOADER, PluginLoader)


def _load_content_types():
    _check_path(_TYPES_DIR)
    descriptors = _load_type_descriptors(_TYPES_DIR)
    _load_type_definitions(descriptors)


def _load_distributors():
    _check_path(_DISTRIBUTORS_DIR)
    _LOADER.load_distributors_from_path(_DISTRIBUTORS_DIR)


def _load_importers():
    _check_path(_IMPORTERS_DIR)
    _LOADER.load_importers_from_path(_IMPORTERS_DIR)


def _load_profilers():
    _check_path(_PROFILERS_DIR)
    _LOADER.load_profilers_from_path(_PROFILERS_DIR)


def _load_type_definitions(descriptors):
    definitions = parser.parse(descriptors)
    database.update_database(definitions)


def _load_type_descriptors(path):
    descriptors = []
    for file_name in os.listdir(path):
        content = _read_content(file_name)
        descriptor = TypeDescriptor(file_name, content)
        descriptors.append(descriptor)
    return descriptors


def _validatie_importers():
    assert isinstance(_LOADER, PluginLoader)
    supported_types = list_content_types()
    for plugin_name, plugin_types in _LOADER.get_loaded_importers().items():
        for type_ in plugin_types:
            if type_ in supported_types:
                continue
            msg = _('Importer %(i)s: not type definition found for %(t)s')
            raise PluginLoadError(msg % {'i': plugin_name, 't': type_})

# plugin loading

def _add_path_to_sys_path(path):
    if path in sys.path:
        return
    sys.path.append(path)


def _get_plugin_dirs(plugin_root):
    dirs = []
    for entry in os.listdir(plugin_root):
        if not os.path.isdir(entry):
            continue
        plugin_dir = os.path.join(plugin_root, entry)
        dirs.append(plugin_dir)
    return dirs


def _get_plugin_metadata_field(plugin_class, field, default=None):
    metadata = plugin_class.metadata()
    if not isinstance(metadata, dict):
        raise PluginLoadError(_('%(p)s.metadata() did not return a dictionary') %
                              {'p': plugin_class.__name__})
    value = metadata.get(field, default)
    return value


def _get_plugin_types(plugin_class):
    types = _get_plugin_metadata_field(plugin_class, 'types')
    if types is None:
        raise PluginLoadError(_('%(p)s does not define any types') %
                              {'p': plugin_class.__name__})
    if isinstance(types, basestring):
        types = [types]
    return types


def _import_module(name):
    if name in sys.modules:
        sys.modules.pop(name)
    mod = __import__(name)
    for sub in name.split('.')[1:]:
        mod = getattr(mod, sub)
    return mod


def _load_plugin(path, base_class, module_name):
    module_regex = re.compile('%s\.py(c|o)?$' % module_name)
    module_found = False
    package_name = os.path.split(path)[-1]
    config_path = None
    # grok through the directory looking for plugin module and config
    for entry in os.listdir(path):
        if module_regex.match(entry):
            module_found = True
        if _CONFIG_REGEX.match(entry):
            config_path = os.path.join(path, entry)
    # if we can't find the module, error out
    if not module_found:
        msg = _('%(n)s plugin has no module: %(p)s.%(m)s')
        d = {'n': module_name.title(), 'p': package_name, 'm': module_name}
        raise PluginLoadError(msg % d)
    # load and return the plugin class and configuration
    cls = _load_plugin_class('.'.join(package_name, module_name), base_class)
    cfg = {}
    if config_path is not None:
        cfg = _load_plugin_config(config_path)
    # TODO log successful loading of plugin
    return (cls, cfg)


def _load_plugin_config(config_file_name):
    contents = _read_content(config_file_name)
    cfg = json.loads(contents)
    return cfg


def _load_plugin_class(module_name, base_class):
    module = _import_module(module_name)
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if not isinstance(attr, type) or not issubclass(attr, base_class):
            continue
        return attr
    msg = _('%(m)s modules did not contain a derived class of %(c)s')
    raise PluginLoadError(msg % {'m': module_name, 'c': base_class.__name__})


def _load_plugins_from_path(path, base_class, plugin_map):
    plugin_dirs = _get_plugin_dirs(path)
    for dir_ in plugin_dirs:
        name = os.path.split(dir_)[-1]
        cls, cfg = _load_plugin(dir_, base_class, base_class.__name__.lower())
        types = _get_plugin_types(cls)
        plugin_map.add_plugin(name, cls, cfg, types)

