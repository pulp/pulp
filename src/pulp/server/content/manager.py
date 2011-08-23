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
import itertools
import logging
import os
import re
import sys
from ConfigParser import SafeConfigParser
from gettext import gettext as _

from pulp.server import config
from pulp.server.content.distributor.base import Distributor
from pulp.server.content.importer.base import Importer
from pulp.server.content.types import database, parser
from pulp.server.content.types.model import TypeDescriptor
from pulp.server.pexceptions import PulpException

# constants --------------------------------------------------------------------

_LOG = logging.getLogger(__name__)

_MANAGER = None # Manager instance

# initial type definitions location

_TYPES_DIRECTORY = '/var/lib/pulp'

# initial plugin and configuration file conventions

_TOP_LEVEL_CONFIGS_DIR = '/etc/pulp'
_IMPORTER_CONFIGS_DIR = os.path.join(_TOP_LEVEL_CONFIGS_DIR, 'importers')
_DISTRIBUTOR_CONFIGS_DIR = os.path.join(_TOP_LEVEL_CONFIGS_DIR, 'distributors')

_TOP_LEVEL_PLUGINS_DIR = os.path.dirname(__file__)
_IMPORTER_PLUGINS_DIR = os.path.join(_TOP_LEVEL_PLUGINS_DIR, 'importers')
_DISTRIBUTOR_PLUGINS_DIR = os.path.join(_TOP_LEVEL_PLUGINS_DIR, 'distributors')

_TOP_LEVEL_PLUGINS_PACKAGE = 'pulp.server.content'
_IMPORTER_PLUGINS_PACKAGE = '.'.join((_TOP_LEVEL_PLUGINS_PACKAGE, 'importers'))
_DISTRIBUTOR_PLUGINS_PACKAGE = '.'.join((_TOP_LEVEL_PLUGINS_PACKAGE, 'distributors'))

# exceptions -------------------------------------------------------------------

class ManagerException(PulpException):
    """
    Base manager exception class.
    """
    pass


class ConflictingPluginError(ManagerException):
    """
    Raised when two or more plugins try to handle the same content or
    distribution type(s).
    """
    pass


class MalformedPluginError(ManagerException):
    """
    Raised when a plugin does not provide required information or pass a sanity
    check.
    """
    pass

# manager class utils ----------------------------------------------------------

def _check_path(path):
    """
    Check a path for existence and read permissions.
    @type path: str
    @param path: file system path to check
    @raise ValueError: if path does not exist or is unreadable
    """
    if os.access(path, os.F_OK | os.R_OK):
        return
    raise ValueError(_('Cannot find path %s') % path)


def _load_configs(config_paths):
    """
    Load and parse plugin cofiguration files from the list directories.
    @type config_paths: list of strs
    @params config_paths: list of directories
    @rtype: dict
    @return: map of config name to SafeConfigParser instance
    """
    configs = {}
    files_regex = re.compile('.*\.conf$')
    for path in config_paths:
        files = os.listdir(path)
        for file_name in filter(files_regex.match, files):
            if file_name in configs:
                raise ConflictingPluginError(_('More than one configuration file found for %s') % file_name)
            parser = SafeConfigParser()
            parser.read(os.path.join(path, file_name))
            configs[file_name] = parser
    return configs


def _import_module(name):
    """
    Given the name of a python module, import it.
    @type name: str
    @param name: name of the module to import
    @rtype: module
    @return: python module corresponding to given name
    """
    if name in sys.modules:
        del sys.modules[name]
    mod = __import__(name)
    for sub in name.split('.')[1:]:
        mod = getattr(mod, sub)
    return mod


def _load_modules(plugin_paths, skip=None):
    """
    Load python modules from the list of plugin directories.
    @type plugin_paths: tuple or list of strs
    @param plugin_paths: list of directories
    @type skip: tuple or list of strs
    @param skip: optional list of module names to skip
    @rtype: list of modeule instances
    @return: all modules in the list of directories not in the skip list
    """
    skip = skip or ('__init__', 'base') # don't load package or base modules
    files_regex = re.compile('(?!(%s))\.py$' % '|'.join(skip))
    modules = []
    for path, package_name in plugin_paths.items():
        files = os.listdir(path)
        for file_name in filter(files_regex.match, files):
            name = file_name.rsplit('.', 1)[0]
            module_name = '.'.join((package_name, name))
            module = _import_module(module_name)
            modules.append(module)
    return modules


def _is_plugin_enabled(pulgin_name, config):
    """
    Grok through a config parser and see if the plugin is not disabled.
    @type config: SafeConfigParser instance
    @param config: plugin config
    @rtype: bool
    @return: True if the plugin is enabled, False otherwise
    """
    if config is None:
        return True
    if not config.has_section(plugin_name):
        return True
    if not config.has_option(plugin_name, 'enabled'):
        return True
    return config.getboolean(plugin_name, 'enabled')


def _load_plugins(cls, plugin_paths, config_paths, plugin_dict, config_dict):
    """
    Load various various plugins of type "cls" and their configurations from the
    provided paths into the provided dictionaries.
    @type cls: Plugin class instance
    @param cls: plugin class to load
    @type plugin_paths: list of strs
    @param plugin_paths: directories to load plugin modules from
    @type config_paths: list of strs
    @param config_paths: directories to load configuration files from
    @type plugin_dict: dict
    @param plugin_dict: dictionary to store plugin classes in
    @type config_dict: dict
    @param config_dict: dictionary to story parsed configuration files in
    """
    configs = _load_configs(config_paths)
    modules = _load_modules(plugin_paths)
    for module in modules:
        for attr in dir(module):
            if not issubclass(attr, cls):
                continue
            metadata = attr.metadata()
            if not isinstance(metadata, dict):
                raise MalformedPluginError(_('%s metadata() did not return a dict: %s') %
                                           (cls.__name__, attr.__name__))
            name = metadata.get('name', None)
            version = metadata.get('version', None)
            types = metadata.get('types', ())
            conf_file = metadata.get('conf_file', None)
            if name is None:
                raise MalformedPluginError(_('%s discoverd with no name metadata: %s') %
                                           (cls.__name__, attr.__name__))
            cfg = configs.get(conf_file, None)
            if not _is_plugin_enabled(name, cfg):
                continue
            plugin_versions = plugin_dict.setdefault('name', {})
            if version in plugin_versions:
                raise ConflictingPluginError(_('Two %s plugins %s version %s found') %
                                             (cls.__name__, name, str(version)))
            plugin_versions[version] = attr
            config_versions = config_dict.setdefault('name', {})
            config_versions[version] = cfg or SafeConfigParser()
            _LOG.info(_('%s plugin %s version %s loaded for content types: %s') %
                      (cls.__name__, name, str(version), ','.join(types)))


def _get_versioned_dict_value(d, key, version=None):
    """
    Do a lookup in a dictionary whos values are dictionaries keyed by version.
    @type d: dict
    @param d: dictionary to do lookup in.
    @type key: any immutable
    @param key: key to lookup versions for
    @type version: any immutable
    @param version: version of value to return, None returns the highest version
    @rtype: any
    @return: value for the given key and version, None if lookup fails
    """
    versions = d.get(key, None)
    if versions is None:
        return None
    if version is None:
        version = max(versions)
    return versions.get(version, None)

# manager class ----------------------------------------------------------------

class Manager(object):
    """
    Plugin manager class that discovers and associates importer and distributor
    plugin with content types.
    """
    def __init__(self):
        self.importer_config_paths = []
        self.importer_plugin_paths = {}
        self.distributor_config_paths = []
        self.distributor_plugin_paths = {}

        self.importer_configs = {}
        self.importer_plugins = {}
        self.distributor_configs = {}
        self.distributor_plugins = {}

    # plugin discovery configuration

    def add_importer_config_path(self, path):
        """
        Add a directory for importer configuration files.
        @type path: str
        @param path: importer configuration directory
        """
        _check_path(path)
        self.importer_config_paths.append(path)

    def add_importer_plugin_path(self, path, package_name=None):
        """
        Add a directory for importer plugins and associated package name.
        @type path: str
        @param path: importer plugin directory
        @type package_name: str or None
        @param package_name: optional package name for importation
        """
        _check_path(path)
        self.importer_plugin_paths[path] = package_name or ''

    def add_distributor_config_path(self, path):
        """
        Add a directory for distributor configuration files.
        @type path: str
        @param path: distributor configuration directory
        """
        _check_path(path)
        self.distributor_config_paths.append(path)

    def add_distributor_plugin_path(self, path, package_name=None):
        """
        Add a directory for distributor plugins and associate package name.
        @type path: str
        @param path: distributor plugin directory
        @type package_name: str or None
        @param package_name: optional package name for importation
        """
        _check_path(path)
        self.distributor_plugin_paths[path] = package_name or ''

    # plugin discovery

    def validate_importers(self):
        """
        Validate the importers supported content types, removing and importers
        that are for content types not found in the content types database.
        """
        supported_types = list_content_types()
        for name, versions in tuple(self.importer_plugins.items()):
            for version, cls in tuple(versions.items()):
                for content_type in cls.metadata().get('types', ()):
                    if content_type not in supported_types:
                        msg = _('Unloading importer %s, version %s: unsupported content type %s')
                        _LOG.error(msg % (name, version, content_type))
                        del self.importer_plugins[name][version]
                        del self.importer_configs[name][version]
                        continue
            if not versions:
                del self.importer_plugins[name]
                del self.importer_configs[name]

    def load_importers(self, validate=False):
        """
        Load all importer modules and associate them with their supported types.
        """
        assert not (self.importer_plugins or self.importer_configs)
        _load_plugins(Importer,
                      self.importer_plugin_paths,
                      self.importer_config_paths,
                      self.importer_plugins,
                      self.importer_configs)
        if validate:
            self.validate_importers()

    def load_distributors(self):
        """
        Load all distributor modules and associate them with their supported types.
        """
        assert not (self.distributor_plugins or self.distributor_configs)
        _load_plugins(Distributor,
                      self.distributor_plugin_paths,
                      self.distributor_config_paths,
                      self.distributor_plugins,
                      self.distributor_configs)

    # importer/distributor lookup api

    def get_importer_class_by_name(self, name, version=None):
        """
        Get an importer class by name and version.
        @type name: str
        @param name: importer class name
        @type version: None or int
        @param version: version of plugin class to get, None means highest
        @rtype: L{Importer} class
        @return: importer class or None if no importer class is found
        """
        cls = _get_versioned_dict_value(self.importer_plugins, name, version)
        return cls

    def get_importer_config_by_name(self, name, version=None):
        """
        Get an importer configuration by name and version.
        @type name: str
        @param name: importer configuration name
        @type version: None or int
        @param version: version of plugin configuration to get, None means highest
        @rtype: L{Importer} class
        @return: importer configuration or None if no importer configuration is found
        """
        cfg = _get_versioned_dict_value(self.importer_configs, name, version)
        return cfg

    def get_distributor_class_by_name(self, name, version=None):
        """
        Get an distributor class by name and version.
        @type name: str
        @param name: distributor class name
        @type version: None or int
        @param version: version of plugin class to get, None means highest
        @rtype: L{Distributor} class
        @return: distributor class or None if no distributor class is found
        """
        cls = _get_versioned_dict_value(self.distributor_plugins, name, version)
        return cls

    def get_distributor_config_by_name(self, name, version=None):
        """
        Get an distributor configuration by name and version.
        @type name: str
        @param name: distributor configuration name
        @type version: None or int
        @param version: version of plugin configuration to get, None means highest
        @rtype: L{Distributor} class
        @return: distributor configuration or None if no distributor configuration is found
        """
        cfg = _get_versioned_dict_value(self.distributor_configs, name, version)
        return cfg

    # query api

    def get_loaded_importers(self):
        """
        Return the loaded importer classes and their versions.
        @rtype: list of tuples
        @return: list of tuples: importer name, list of versions
        """
        return [(i, sorted(v.keys())) for i, v in self.importer_plugins.items()]

    def get_loaded_distributors(self):
        """
        Return the loaded distributor classes and their versions.
        @rtype: list of tuples
        @return: list of tuples: distributor name, list of versions
        """
        return [(i, sorted(v.keys())) for i, v in self.distributor_plugins.items()]

# content type initialization utils --------------------------------------------

def _read_contents(file_name):
    handle = open(file_name, 'r')
    contents = handle.read()
    handle.close()
    return contents


def _load_type_descriptors(path):
    descriptors = []
    for file_name in os.listdir(path):
        contents = _read_contents(file_name)
        descriptor = TypeDescriptor(file_name, contents)
        descriptors.append(descriptor)
    return descriptors


def _load_type_definitions(descriptors):
    definitions = parser.parse(descriptors)
    database.update_database(definitions)


def _load_content_types():
    _check_path(_TYPES_DIRECTORY)
    descriptors = _load_descriptors(_TYPES_DIRECTORY)
    _load_type_definitions(descriptors)


# manager initialization utils -------------------------------------------------

def _create_manager():
    global _MANAGER
    _MANAGER = Manager()


def _add_importer_and_distributor_paths():
    # add the pulp conventional importer and distributor paths
    _MANAGER.add_importer_config_path(_IMPORTER_CONFIGS_DIR)
    _MANAGER.add_importer_plugin_path(_IMPORTER_PLUGINS_DIR,
                                      _IMPORTER_PLUGINS_PACKAGE)
    _MANAGER.add_distributor_config_path(_DISTRIBUTOR_CONFIGS_DIR)
    _MANAGER.add_distributor_plugin_path(_DISTRIBUTOR_PLUGINS_DIR,
                                         _DISTRIBUTOR_PLUGINS_PACKAGE)


def _load_importers_and_distributors():
    _MANAGER.load_importers(validate=True)
    _MANAGER.load_distributors()

# manager api ------------------------------------------------------------------

def initialize():
    """
    Initialize importer/distributor plugin discovery and association.
    """
    # NOTE this is broken down into the the utility functions: _create_manager,
    # _add_paths, and _load_plugins to facilitate testing and other alternate
    # control flows on startup
    global _MANAGER
    assert _MANAGER is None
    _load_content_types()
    _create_manager()
    _add_importer_and_distributor_paths()
    _load_importers_and_distributors()


def finalize():
    """
    Cleanup the plugn manager.
    """
    # NOTE this is not necessary for the pulp server but is provided for testing
    global _MANAGER
    assert _MANAGER is not None
    tmp = _MANAGER
    _MANAGER = None
    del tmp

# query api --------------------------------------------------------------------

def list_importers():
    """
    List the loaded importers
    @rtype: list
    @return: list of tuples: importer name, list of versions
    """
    assert _MANAGER is not None
    return _MANAGER.get_loaded_importers()


def list_distributors():
    """
    List the loaded distributors
    @rtype: list
    @return: list of tuples: distributor name, list of versions
    """
    assert _MANAGER is not None
    return _MANAGER.get_loaded_distributors()


def list_content_types():
    """
    List the supported content types.
    @rtype: list of str's
    @return: list of content type definitions in the database
    """
    return database.all_type_collection_names()

# plugin api -------------------------------------------------------------------

def get_importer_by_name(name, version=None):
    """
    Get an importer instance for a given name and version.
    @type name: str
    @param name: name of the importer instance to get
    @type version: None or int
    @param version: optional version, None means to use the latest version
    @rtype: L{Importer} instance or None
    @return: importer for the given name and version, None if one isn't found
    """
    assert _MANAGER is not None
    cls = _MANAGER.get_importer_class_by_name(name, version)
    if cls is None:
        return None
    cfg = _MANAGER.get_importer_config_by_name(name, version)
    importer = cls(cfg)
    return importer


def get_distributor_by_name(name, version=None):
    """
    Get an distributor instance for a given name and version.
    @type name: str
    @param name: name of the distributor instance to get
    @type version: None or int
    @param version: optional version, None means to use the latest version
    @rtype: L{Distributor} instance or None
    @return: distributor for the given name and version, None if one isn't found
    """
    assert _MANAGER is not None
    cls = _MANAGER.get_distributor_class_by_name(name, version)
    if cls is None:
        return None
    cfg = _MANAGER.get_distributor_config_by_name(name, version)
    distributor = cls(cfg)
    return distributor
