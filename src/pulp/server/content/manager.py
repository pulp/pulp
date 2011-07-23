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

import os
import re
from ConfigParser import SafeConfigParser
from gettext import gettext as _

from pulp.server import config
from pulp.server.content.distributor.base import Distributor
from pulp.server.content.importer.base import Importer
from pulp.server.content.module import import_module
from pulp.server.pexceptions import PulpException

# exceptions -------------------------------------------------------------------

class PluginNotFoundError(PulpException):
    pass

# manager instance -------------------------------------------------------------

_manager = None

# manager class ----------------------------------------------------------------

class Manager(object):
    """
    Plugin manager class that discovers and associates importer and distributor
    plugin with content types.
    """
    def __init__(self):
        self.importer_paths = {}
        self.distributor_paths = {}
        self.importers = {}
        self.distributors = {}
        self.configured_importers = self.__configured_importers()
        self.configured_distributors = self.__configured_distributors()
        self.importer_configs = {}
        self.distributor_configs = {}

    def __configured_importers(self):
        cfg = {}
        if not config.config.has_section)'importers'):
            return cfg
        for content_type in config.config.options('importers'):
            cfg[content_type] = config.config.getboolean('importers', content_type)
        return cfg

    def __configured_distributors(self):
        cfg = {}
        if not config.config.has_section('distributors'):
            return cfg
        for distribution_type in config.config.options('distributors'):
            cfg[distribution_type] = config.config.getboolean('distributors', distribution_type)
        return cfg

    def add_importer_path(self, path, package_name=None):
        """
        Add a path for the importer modules.
        @type path: str
        @param path: filesystem path to python package containing importer modules
        @type package_name: None or str
        @param package_name: optional fully qualified package name, defaults to ''
        @raises ValueError: if the path is not found or cannot be read
        """
        if not os.access(path, os.F_OK | os.R_OK):
            raise ValueError(_('Cannot find path %s') % path)
        self.importer_paths[path] = package_name or ''

    def add_distributor_path(self, path, package_name=None):
        """
        Add a path for the distributor modules.
        @type path: str
        @param path: filesystem path to python package containing distributor modules
        @type package_name: None or str
        @param package_name: optional fully qualified package name, defaults to ''
        @raises ValueError: if the path is not found or cannot be read
        """
        if not os.access(path, os.F_OK | os.R_OK):
            raise ValueError(_('Cannot find path %s') % path)
        self.distributor_paths[path] = package_name or ''

    def _load_modules(self, paths, skip=None):
        """
        Helper method that loads modules from the given package paths.
        @type paths: dict
        @param patsh: a mapping of package directory paths to package names
        @type skip: tuple or list
        @param skip: list of module names to *not* load
        @rtype: list of modules
        @return: list of all modules in all packages in the paths
        """
        assert isinstance(paths, dict)
        skip = skip or ('__init__',)
        files_regex = re.compile('(?!(%s)).*\.py$') % '|'.join(skip)
        modules = []
        for path, package_name in paths.items():
            files = os.listdir(path)
            for file_name in filter(files_regex.match, files):
                name = '.'.join((package_name, file_name.rsplit('.', 1)[0]))
                module = import_module(name)
                modules.append(module)
        return modules

    def load_importers(self):
        """
        Load all importer modules and associate them with their supported types.
        """
        assert not self.importers
        modules = self._load_modules(self.importer_paths, ('__init__', 'base'))
        for module in modules:
            for attr in dir(module):
                if not issubclass(attr, Importer):
                    continue
                cfg = SafeConfigParser
                cfg.read(attr.config_files)
                for content_type in attr.types:
                    # TODO log error or raise exception or something
                    if content_type in self.importers:
                        continue
                    self.importers[content_type] = attr
                    self.importer_configs[content_type] = cfg

    def load_distributors(self):
        """
        Load all distributor modules and associate them with their supported types.
        """
        assert not self.distributors
        modules = self._load_modules(self.distributor_paths, ('__init__', 'base'))
        for module in modules:
            for attr in dir(module):
                if not issubclass(attr, Distributor):
                    continue
                cfg = SafeConfigParser()
                cfg.read(attr.config_files)
                for distribution_type in attr.types:
                    if distribution_type in self.distributors:
                        # TODO log error
                        continue
                    self.distributors[distribution_type] = attr
                    self.distributor_configs[distribution_type] = cfg

    def lookup_importer_class(self, content_type):
        """
        Retrieve an importer class associated with the given content type.
        @type content_type: str
        @param content_type: content type label
        @rtype: Importer class or None
        @return: importer class associated with the the content type or None if
                 no associated importer class is found
        """
        if not self.configured_importers.get(content_type, True):
            return None
        return self.importers.get(content_type, None)

    def lookup_importer_config(self, content_type):
        """
        Return the (potentially empty) importer config for the given content type.
        @type content_type: str
        @param content_type: content type to get importer config for
        @rtype: SafeConfigParser instance
        @return: importer config for given content type
        """
        return self.importer_configs.get(content_type, SafeConfigParser())

    def lookup_distributor_class(self, distribution_type):
        """
        Retrieve a distributor class associated with the given distribution type.
        @type distribution_type: str
        @param distribution_type: content type label
        @rtype: Distributor class or None
        @return: distributor class associated with the the distribution type or
                 None if no associated distributor class is found
        """
        if not self.configured_distributors.get(distribution_type, True):
            return None
        return self.distributors.get(distribution_type, None)

    def lookup_distributor_config(self, distributor_type):
        """
        Return the (potentially empty) distributor config for the given content type.
        @type content_type: str
        @param content_type: content type to get distributor config for
        @rtype: SafeConfigParser instance
        @return: distributor config for given content type
        """
        return self.distributor_configs.get(distributor_type, SafeConfigParser())

# manager api ------------------------------------------------------------------

def _create_manager():
    global _manager
    _manager = Manager()


def _add_paths(importer_paths, distributor_paths):
    for p, n in importer_paths.items():
        _manager.add_importer_path(p, n)
    for p, n in distributor_paths.items():
        _manager.add_distributor_path(p, n)


def _load_plugins():
    _manager.load_importers()
    _manager.load_distributors()


def initialize():
    """
    Initialize importer/distributor plugin discovery and association.
    """
    # NOTE this is broken down into the the helper functions: _create_manager,
    # _add_paths, and _load_plugins to facilitate testing and other alternate
    # control flows on startup
    global _manager
    assert _manager is None
    local_path = os.path.dirname(__file__)
    importer_paths = {os.path.join(local_path, 'importer'):
                      'pulp.server.content.importer'}
    distributor_paths = {os.path.join(local_path, 'distributor'):
                         'pulp.server.content.distributor'}
    _create_manager()
    _add_paths(importer_paths, distributor_paths)
    _load_plugins()


def finalize():
    """
    Conduct and necessary cleanup of the plugn manager.
    """
    # NOTE this is not necessary for the pulp server but is provided for testing
    global _manager
    assert _manager is not None
    tmp = _manager
    _manager = None
    del tmp


def get_importer(content_type):
    """
    Get an importer for the given content type.
    @type content_type: str
    @param content_type: content type label
    @rtype: Importer instance
    @return: importer associated with content type
    @raises PluginNotFoundError: if not importer is associated with the content type
    """
    # TODO allow client to pass in constructor arguments/options
    assert _manager is not None
    cls = _manager.lookup_importer_class(content_type)
    if cls is None:
        raise PluginNotFoundError(_('No importer found for %s') % content_type)
    cfg = _manager.lookup_importer_config(content_type)
    return cls(config=cfg)


def get_distributor(distribution_type):
    """
    Get a distributor for the give distribution type.
    @type distribution_type: str
    @param distribution_type: distribution type label
    @rtype: Distributor instance
    @return: distributor associated with the distribution type
    @raises PluginNotFoundError: if not importer is associated with the distribution type
    """
    # TODO allow client to pass in constructor arguments/options
    assert _manager is not None
    cls = _manager.lookup_distributor_class(distribution_type)
    if cls is None:
        raise PluginNotFoundError(_('No distributor found for %s') % distribution_type)
    cfg = _manager.lookup_distributor_config(distribution_type)
    return cls(config=cfg)
