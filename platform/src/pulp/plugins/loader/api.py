# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import logging
import os
from gettext import gettext as _

from pulp.plugins.distributor import Distributor, GroupDistributor
from pulp.plugins.importer import Importer, GroupImporter
from pulp.plugins.loader import exceptions as loader_exceptions
from pulp.plugins.loader import loading
from pulp.plugins.loader.manager import PluginManager
from pulp.plugins.profiler import Profiler
from pulp.plugins.types import database, parser
from pulp.plugins.types.model import TypeDescriptor

# constants --------------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# implicit singleton instance of PluginManager

_MANAGER = None

# plugin locations

_PLUGINS_ROOT = '/usr/lib/pulp/plugins'
_DISTRIBUTORS_DIR = _PLUGINS_ROOT + '/distributors'
_IMPORTERS_DIR = _PLUGINS_ROOT + '/importers'
_GROUP_DISTRIBUTORS_DIR = _PLUGINS_ROOT + '/group_distributors'
_GROUP_IMPORTERS_DIR = _PLUGINS_ROOT + '/group_importers'
_PROFILERS_DIR = _PLUGINS_ROOT + '/profilers'
_TYPES_DIR = _PLUGINS_ROOT + '/types'

# state management -------------------------------------------------------------

def initialize(validate=True):
    """
    Initialize the loader module by loading all type definitions and plugins.
    @param validate: if True, perform post-initialization validation
    @type validate: bool
    """

    global _MANAGER
    # pre-initialization validation
    assert not _is_initialized()

    # initialization
    _load_content_types(_TYPES_DIR)

    _create_manager()
    # add plugins here in the form (path, base class, manager map)
    plugin_tuples =  ((_DISTRIBUTORS_DIR, Distributor, _MANAGER.distributors),
                      (_DISTRIBUTORS_DIR, GroupDistributor, _MANAGER.group_distributors),
                      (_IMPORTERS_DIR, GroupImporter, _MANAGER.group_importers),
                      (_IMPORTERS_DIR, Importer, _MANAGER.importers),
                      (_PROFILERS_DIR, Profiler, _MANAGER.profilers))
    for path, base_class, plugin_map in plugin_tuples:
        loading.load_plugins_from_path(path, base_class, plugin_map)

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

    global _MANAGER
    assert _is_initialized()
    _MANAGER = None

# query api --------------------------------------------------------------------

def list_content_types():
    """
    List the supported content types.
    @return: list of content type IDs
    @rtype: list of str
    """
    assert _is_initialized()
    return database.all_type_ids()


def list_distributors():
    """
    List the loaded distributors.
    @return: dictionary of distributor names -> metadata
    @rtype: dict {str: dict, ...}
    """
    assert _is_initialized()
    return _MANAGER.distributors.get_loaded_plugins()


def list_importers():
    """
    List the loaded importers.
    @return: dictionary of importer names: metadata
    @rtype: dict {str: dict, ...}
    """
    assert _is_initialized()
    return _MANAGER.importers.get_loaded_plugins()


def list_profilers():
    """
    List the loaded profilers.
    @return: dictionary of profiler names: metadata
    @rtype: dict {str: dict, ...}
    """
    assert _is_initialized()
    return _MANAGER.profilers.get_loaded_plugins()


def list_distributor_types(id):
    """
    List the supported distribution types for the given distributor id.
    @param id: id of the distributor
    @type id: str
    @return: tuple of types supported by the distributor
    @rtype: tuple
    @raise: L{PluginNotFound} if no distributor corresponds to the id
    """
    assert _is_initialized()
    types = _MANAGER.distributors.get_loaded_plugins().get(id, None)
    if types is None:
        raise loader_exceptions.PluginNotFound(_('No plugin found: %(n)s') % {'n': id})
    return types


def list_importer_types(id):
    """
    List the supported content types for the given importer id.

    This should be the signature:
      return: tuple of types supported by the importer
      rtype: tuple
    However it's actually returning a dict where the types are under key
    "types". I don't have time to dig into what is calling this to fix it,
    so for now I'm fixing the docs.

    @param id: id of the importer
    @type id: str

    @return: dict containing the type IDs at key "types"
    @rtype:  dict {str : list}

    @raise: L{PluginNotFound} if no importer corresponds to the id
    """
    assert _is_initialized()
    types = _MANAGER.importers.get_loaded_plugins().get(id, None)
    if types is None:
        raise loader_exceptions.PluginNotFound(_('No plugin found: %(n)s') % {'n': id})
    return types


def list_profiler_types(id):
    """
    List the supported profile types for the given profiler id.
    @param id: id of the profiler
    @type id: str
    @return: tuple of types supported by the profiler
    @rtype: tuple
    @raise: L{PluginNotFound} if no profiler corresponds to the id
    """
    assert _is_initialized()
    types = _MANAGER.profilers.get_loaded_plugins().get(id, None)
    if types is None:
        raise loader_exceptions.PluginNotFound(_('No plugin found: %(n)s') % {'n': id})
    return types


def is_valid_distributor(id):
    """
    Check to see that a distributor exists for the given id.
    @param id: id of the distributor
    @type id: str
    @return: True if the distributor exists, False otherwise
    @rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.distributors.get_loaded_plugins()
    return id in plugins


def is_valid_group_distributor(id):
    """
    Checks to see that a group distributor exists for the given id.
    @param id: id of the group distributor
    @type  id: str
    @return: true if the group distributor exists; false otherwise
    @rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.group_distributors.get_loaded_plugins()
    return id in plugins


def is_valid_importer(id):
    """
    Check to see that a importer exists for the given id.
    @param id: id of the importer
    @type id: str
    @return: True if the importer exists, False otherwise
    @rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.importers.get_loaded_plugins()
    return id in plugins


def is_valid_group_importer(id):
    """
    Checks to see that a group importer exists for the given id.
    @param id: id of the group importer
    @type  id: str
    @return: true if the group importer exists; false otherwise
    @rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.group_importers.get_loaded_plugins()
    return id in plugins


def is_valid_profiler(id):
    """
    Check to see that a profiler exists for the given id.
    @param id: id of the profiler
    @type id: str
    @return: True if the profiler exists, False otherwise
    @rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.importers.get_loaded_plugins()
    return id in plugins

# plugin api -------------------------------------------------------------------

def get_distributor_by_id(id):
    """
    Get a distributor instance that corresponds to the given id.
    @param id: id of the distributor
    @type id: str
    @return: tuple of L{Distributor} instance and dictionary configuration
    @rtype: tuple (L{Distributor}, dict)
    @raise: L{PluginNotFound} if no distributor corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.distributors.get_plugin_by_id(id)
    return cls(), cfg


def get_importer_by_id(id):
    """
    Get an importer instance that corresponds to the given id.
    @param id: id of the importer
    @type id: str
    @return: tuple of L{Importer} instance and dictionary configuration
    @rtype: tuple (L{Importer}, dict)
    @raise: L{PluginNotFound} if no importer corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.importers.get_plugin_by_id(id)
    return cls(), cfg


def get_group_distributor_by_id(id):
    """
    Get a group distributor instance that corresponds to the given id.
    @param id: id of the group distributor
    @type id: str
    @return: tuple of L{GroupDistributor} instance and dictionary configuration
    @rtype: tuple (L{GroupDistributor}, dict)
    @raise: L{PluginNotFound} if no group distributor corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.group_distributors.get_plugin_by_id(id)
    return cls(), cfg


def get_group_importer_by_id(id):
    """
    Get a group importer instance that corresponds to the given id.
    @param id: id of the group importer
    @type id: str
    @return: tuple of L{GroupImporter} instance and dictionary configuration
    @rtype: tuple (L{GroupImporter}, dict)
    @raise: L{PluginNotFound} if no group importer corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.group_importers.get_plugin_by_id(id)
    return cls(), cfg


def get_profiler_by_id(id):
    """
    Get a profiler instance that corresponds to the given id.
    @param id: id of the profiler
    @type id: str
    @return: tuple of L{Profiler} instance and dictionary configuration
    @rtype: tuple (L{Profiler}, dict)
    @raise: L{PluginNotFound} if no profiler corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.profilers.get_plugin_by_id(id)
    return cls(), cfg

def get_profiler_by_type(type_id):
    """
    Get a profiler instance that supports the specified content type.
    @param type_id: content type
    @type type_id: str
    @return: tuple of L{Profiler} instance and dictionary configuration
    @rtype: tuple (L{Profiler}, dict)
    @raise: L{PluginNotFound} if no profiler corresponds to the id
    """
    assert _is_initialized()
    ids = _MANAGER.profilers.get_plugin_ids_by_type(type_id)
    # this makes the assumption that there is only 1 profiler per type
    cls, cfg = _MANAGER.profilers.get_plugin_by_id(ids[0])
    return cls(), cfg

# initialization methods -------------------------------------------------------

def _is_initialized():
    """
    @rtype: bool
    """
    return isinstance(_MANAGER, PluginManager)

def _create_manager():
    global _MANAGER
    _MANAGER = PluginManager()

def _load_content_types(types_dir):
    """
    @type types_dir: str
    """
    if not os.access(types_dir, os.F_OK | os.R_OK):
        msg = _('Cannot load types: path does not exist or cannot be read: %(p)s')
        _LOG.critical(msg % {'p': types_dir})
        return
    descriptors = _load_type_descriptors(types_dir)
    _load_type_definitions(descriptors)


def _load_type_descriptors(path):
    """
    @type path: str
    @rtype: list [L{TypeDescriptor}, ...]
    """
    _LOG.debug('Loading type descriptors from: %s' % path)
    descriptors = []
    for file_name in os.listdir(path):
        full_file_name = os.path.join(path, file_name)
        content = loading.read_content(full_file_name)
        descriptor = TypeDescriptor(file_name, content)
        descriptors.append(descriptor)
    return descriptors


def _load_type_definitions(descriptors):
    """
    @type descriptors: list [L{TypeDescriptor}, ...]
    """
    definitions = parser.parse(descriptors)
    database.update_database(definitions)


def _validate_importers():
    """
    @raise: L{PluginLoadError}
    """
    assert _is_initialized()
    supported_types = list_content_types()
    for plugin_id, metadata in _MANAGER.importers.get_loaded_plugins().items():
        for type_ in metadata['types']:
            if type_ in supported_types:
                continue
            msg = _('Importer %(i)s: no type definition found for %(t)s')
            raise loader_exceptions.InvalidImporter(msg % {'i': plugin_id, 't': type_})


