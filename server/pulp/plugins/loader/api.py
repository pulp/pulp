# Copyright (c) 2011-2012 Red Hat, Inc.
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
from pulp.plugins.cataloger import Cataloger
from pulp.plugins.types import database, parser
from pulp.plugins.types.model import TypeDescriptor

_logger = logging.getLogger('db')

# implicit singleton instance of PluginManager

_MANAGER = None

# constants --------------------------------------------------------------------

# entry point names
ENTRY_POINT_EXTENSIONS = 'pulp.extensions'
ENTRY_POINT_DISTRIBUTORS = 'pulp.distributors'
ENTRY_POINT_GROUP_DISTRIBUTORS = 'pulp.group_distributors'
ENTRY_POINT_IMPORTERS = 'pulp.importers'
ENTRY_POINT_GROUP_IMPORTERS = 'pulp.group_importers'
ENTRY_POINT_PROFILERS = 'pulp.profilers'
ENTRY_POINT_CATALOGERS = 'pulp.catalogers'

# plugin locations

_PLUGINS_ROOT = '/usr/lib/pulp/plugins'
_TYPES_DIR = _PLUGINS_ROOT + '/types'

# state management -------------------------------------------------------------


def initialize(validate=True):
    """
    Initialize the loader module by loading all type definitions and plugins.
    :param validate: if True, perform post-initialization validation
    :type validate: bool
    """

    global _MANAGER
    # No need to do this twice, so if we're already initialized we just return
    if _is_initialized():
        return

    _create_manager()

    plugin_entry_points = (
        (ENTRY_POINT_DISTRIBUTORS, _MANAGER.distributors),
        (ENTRY_POINT_GROUP_DISTRIBUTORS, _MANAGER.group_distributors),
        (ENTRY_POINT_IMPORTERS, _MANAGER.importers),
        (ENTRY_POINT_GROUP_IMPORTERS, _MANAGER.group_importers),
        (ENTRY_POINT_PROFILERS, _MANAGER.profilers),
        (ENTRY_POINT_CATALOGERS, _MANAGER.catalogers),
    )
    for entry_point in plugin_entry_points:
        loading.load_plugins_from_entry_point(*entry_point)

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
    :return: list of content type IDs
    :rtype: list of str
    """
    assert _is_initialized()
    return database.all_type_ids()


def list_group_distributors():
    """
    Lists the loaded group distributors.
    :return: dictionary of distributor IDs -> metadata
    :rtype: dict{str: dict, ...}
    """
    assert _is_initialized()
    return _MANAGER.group_distributors.get_loaded_plugins()


def list_distributors():
    """
    List the loaded distributors.
    :return: dictionary of distributor names -> metadata
    :rtype: dict {str: dict, ...}
    """
    assert _is_initialized()
    return _MANAGER.distributors.get_loaded_plugins()


def list_group_importers():
    """
    Lists the loaded group importers.
    :return: dictionary of importer IDs -> metadata
    :rtype: dict{str: dict, ...}
    """
    assert _is_initialized()
    return _MANAGER.group_importers.get_loaded_plugins()


def list_importers():
    """
    List the loaded importers.
    :return: dictionary of importer names: metadata
    :rtype: dict {str: dict, ...}
    """
    assert _is_initialized()
    return _MANAGER.importers.get_loaded_plugins()


def list_profilers():
    """
    List the loaded profilers.
    :return: dictionary of profiler names: metadata
    :rtype: dict {str: dict, ...}
    """
    assert _is_initialized()
    return _MANAGER.profilers.get_loaded_plugins()


def list_catalogers():
    """
    List the loaded catalogers.
    :return: dictionary of catalogers names: metadata
    :rtype: dict {str: dict, ...}
    """
    assert _is_initialized()
    return _MANAGER.catalogers.get_loaded_plugins()


def list_distributor_types(distributor_id):
    """
    List the supported distribution types for the given distributor id.
    :param distributor_id: id of the distributor
    :type distributor_id: str
    :return: tuple of types supported by the distributor
    :rtype: tuple
    :raise: PluginNotFound if no distributor corresponds to the id
    """
    assert _is_initialized()
    types = _MANAGER.distributors.get_loaded_plugins().get(distributor_id, None)
    if types is None:
        raise loader_exceptions.PluginNotFound(_('No plugin found: %(n)s') % {'n': distributor_id})
    return types


def list_importer_types(importer_id):
    """
    List the supported content types for the given importer id.

    This should be the signature:
      return: tuple of types supported by the importer
      rtype: tuple
    However it's actually returning a dict where the types are under key
    "types". I don't have time to dig into what is calling this to fix it,
    so for now I'm fixing the docs.

    :param importer_id: id of the importer
    :type importer_id: str

    :return: dict containing the type IDs at key "types"
    :rtype:  dict {str : list}

    :raise: PluginNotFound if no importer corresponds to the id
    """
    assert _is_initialized()
    types = _MANAGER.importers.get_loaded_plugins().get(importer_id, None)
    if types is None:
        raise loader_exceptions.PluginNotFound(_('No plugin found: %(n)s') % {'n': importer_id})
    return types


def list_profiler_types(profiler_id):
    """
    List the supported profile types for the given profiler id.
    :param profiler_id: id of the profiler
    :type profiler_id: str
    :return: tuple of types supported by the profiler
    :rtype: tuple
    :raise: PluginNotFound if no profiler corresponds to the id
    """
    assert _is_initialized()
    types = _MANAGER.profilers.get_loaded_plugins().get(profiler_id, None)
    if types is None:
        raise loader_exceptions.PluginNotFound(_('No plugin found: %(n)s') % {'n': profiler_id})
    return types


def is_valid_distributor(distributor_id):
    """
    Check to see that a distributor exists for the given id.
    :param distributor_id: id of the distributor
    :type distributor_id: str
    :return: True if the distributor exists, False otherwise
    :rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.distributors.get_loaded_plugins()
    return distributor_id in plugins


def is_valid_group_distributor(group_distributor_id):
    """
    Checks to see that a group distributor exists for the given id.
    :param group_distributor_id: id of the group distributor
    :type  group_distributor_id: str
    :return: true if the group distributor exists; false otherwise
    :rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.group_distributors.get_loaded_plugins()
    return group_distributor_id in plugins


def is_valid_importer(importer_id):
    """
    Check to see that a importer exists for the given id.
    :param importer_id: id of the importer
    :type importer_id: str
    :return: True if the importer exists, False otherwise
    :rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.importers.get_loaded_plugins()
    return importer_id in plugins


def is_valid_group_importer(group_importer_id):
    """
    Checks to see that a group importer exists for the given id.
    :param group_importer_id: id of the group importer
    :type  group_importer_id: str
    :return: true if the group importer exists; false otherwise
    :rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.group_importers.get_loaded_plugins()
    return group_importer_id in plugins


def is_valid_profiler(profiler_id):
    """
    Check to see that a profiler exists for the given id.
    :param profiler_id: id of the profiler
    :type profiler_id: str
    :return: True if the profiler exists, False otherwise
    :rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.profilers.get_loaded_plugins()
    return profiler_id in plugins


def is_valid_cataloger(cataloger_id):
    """
    Check to see that a cataloger exists for the given id.
    :param cataloger_id: id of the cataloger
    :type cataloger_id: str
    :return: True if the cataloger exists, False otherwise
    :rtype: bool
    """
    assert _is_initialized()
    plugins = _MANAGER.catalogers.get_loaded_plugins()
    return cataloger_id in plugins


# plugin api -------------------------------------------------------------------

def get_distributor_by_id(distributor_id):
    """
    Get a distributor instance that corresponds to the given id.
    :param distributor_id: id of the distributor
    :type distributor_id: str
    :return: tuple of Distributor instance and dictionary configuration
    :rtype: tuple (Distributor, dict)
    :raise: PluginNotFound if no distributor corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.distributors.get_plugin_by_id(distributor_id)
    return cls(), cfg


def get_importer_by_id(importer_id):
    """
    Get an importer instance that corresponds to the given id.
    :param importer_id: id of the importer
    :type importer_id: str
    :return: tuple of Importer instance and dictionary configuration
    :rtype: tuple (Importer, dict)
    :raise: PluginNotFound if no importer corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.importers.get_plugin_by_id(importer_id)
    return cls(), cfg


def get_group_distributor_by_id(group_distributor_id):
    """
    Get a group distributor instance that corresponds to the given id.
    :param group_distributor_id: id of the group distributor
    :type group_distributor_id: str
    :return: tuple of GroupDistributor instance and dictionary configuration
    :rtype: tuple (GroupDistributor, dict)
    :raise: PluginNotFound if no group distributor corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.group_distributors.get_plugin_by_id(group_distributor_id)
    return cls(), cfg


def get_group_importer_by_id(group_importer_id):
    """
    Get a group importer instance that corresponds to the given id.
    :param group_importer_id: id of the group importer
    :type group_importer_id: str
    :return: tuple of GroupImporter instance and dictionary configuration
    :rtype: tuple (GroupImporter, dict)
    :raise: PluginNotFound if no group importer corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.group_importers.get_plugin_by_id(group_importer_id)
    return cls(), cfg


def get_profiler_by_id(profiler_id):
    """
    Get a profiler instance that corresponds to the given id.
    :param profiler_id: id of the profiler
    :type profiler_id: str
    :return: tuple of Profiler instance and dictionary configuration
    :rtype: tuple (Profiler, dict)
    :raise: PluginNotFound if no profiler corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.profilers.get_plugin_by_id(profiler_id)
    return cls(), cfg


def get_profiler_by_type(type_id):
    """
    Get a profiler instance that supports the specified content type.
    :param type_id: content type
    :type type_id: str
    :return: tuple of Profiler instance and dictionary configuration
    :rtype: tuple (Profiler, dict)
    :raise: PluginNotFound if no profiler corresponds to the id
    """
    assert _is_initialized()
    ids = _MANAGER.profilers.get_plugin_ids_by_type(type_id)
    # this makes the assumption that there is only 1 profiler per type
    cls, cfg = _MANAGER.profilers.get_plugin_by_id(ids[0])
    return cls(), cfg


def get_cataloger_by_id(catloger_id):
    """
    Get a cataloger instance that corresponds to the given id.
    :param catloger_id: id of the cataloger
    :type catloger_id: str
    :return: tuple of Cataloger instance and dictionary configuration
    :rtype: tuple (Cataloger, dict)
    :raise: PluginNotFound if no cataloger corresponds to the id
    """
    assert _is_initialized()
    cls, cfg = _MANAGER.catalogers.get_plugin_by_id(catloger_id)
    return cls(), cfg


def load_content_types(types_dir=_TYPES_DIR, dry_run=False):
    """
    :type types_dir: str
    """
    if not os.access(types_dir, os.F_OK | os.R_OK):
        msg = _('Cannot load types: path does not exist or cannot be read: %(p)s')
        _logger.critical(msg % {'p': types_dir})
        raise IOError(msg % {'p': types_dir})
    descriptors = _load_type_descriptors(types_dir)
    if dry_run:
        return _check_content_definitions(descriptors)
    else:
        _load_type_definitions(descriptors)

# initialization methods -------------------------------------------------------


def _is_initialized():
    """
    :rtype: bool
    """
    return isinstance(_MANAGER, PluginManager)


def _create_manager():
    global _MANAGER
    _MANAGER = PluginManager()


def _check_content_definitions(descriptors):
    """
    Check whether the given content definitions exist in the database. This method
    does not make any changes to the content definitions or any indexes.

    :param descriptors: A list of content descriptors
    :type  descriptors: list of TypeDescriptor

    :return: A list of content types that would have been created or updated by _load_type_definitions
    :rtype:  list of TypeDefinition
    """
    definitions = parser.parse(descriptors)
    old_content_types = []

    # Ensure all the content types exist and match the definitions
    for definition in definitions:
        content_type = database.type_definition(definition.id)
        if content_type is None:
            old_content_types.append(definition)
            continue

        dict_definition = definition.__dict__
        for key, value in dict_definition.items():
            if key not in content_type or content_type[key] != value:
                old_content_types.append(definition)
                break

    return old_content_types


def _load_type_descriptors(path):
    """
    :type path: str
    :rtype: list [TypeDescriptor, ...]
    """
    _logger.debug('Loading type descriptors from: %s' % path)
    descriptors = []
    for file_name in os.listdir(path):
        full_file_name = os.path.join(path, file_name)
        content = loading.read_content(full_file_name)
        descriptor = TypeDescriptor(file_name, content)
        descriptors.append(descriptor)
    return descriptors


def _load_type_definitions(descriptors):
    """
    :type descriptors: list [TypeDescriptor, ...]
    """
    definitions = parser.parse(descriptors)
    database.update_database(definitions)


def _validate_importers():
    """
    :raise: PluginLoadError
    """
    assert _is_initialized()
    supported_types = list_content_types()
    for plugin_id, metadata in _MANAGER.importers.get_loaded_plugins().items():
        for type_ in metadata['types']:
            if type_ in supported_types:
                continue
            msg = _('Importer %(i)s: no type definition found for %(t)s')
            raise loader_exceptions.InvalidImporter(msg % {'i': plugin_id, 't': type_})
