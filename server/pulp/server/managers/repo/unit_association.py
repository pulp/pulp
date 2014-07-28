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
Contains the manager class and exceptions for handling the mappings between
repositories and content units.
"""
from gettext import gettext as _
import logging
import sys

from celery import task
import pymongo

from pulp.plugins.conduits.unit_import import ImportUnitConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.loader import api as plugin_api
from pulp.server.async.tasks import Task
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.db.model.repository import RepoContentUnit
import pulp.plugins.conduits._common as conduit_common_utils
import pulp.plugins.types.database as types_db
import pulp.server.exceptions as exceptions
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo._common as common_utils


# Shadowed here to remove the need for the caller to import RepoContentUnit
# to get access to them
OWNER_TYPE_IMPORTER = RepoContentUnit.OWNER_TYPE_IMPORTER
OWNER_TYPE_USER = RepoContentUnit.OWNER_TYPE_USER

_OWNER_TYPES = (OWNER_TYPE_IMPORTER, OWNER_TYPE_USER)

# Valid sort strings
SORT_TYPE_ID = 'type_id'
SORT_OWNER_TYPE = 'owner_type'
SORT_OWNER_ID = 'owner_id'
SORT_CREATED = 'created'
SORT_UPDATED = 'updated'

_VALID_SORTS = (SORT_TYPE_ID, SORT_OWNER_TYPE, SORT_OWNER_ID, SORT_CREATED, SORT_UPDATED)

SORT_ASCENDING = pymongo.ASCENDING
SORT_DESCENDING = pymongo.DESCENDING

_VALID_DIRECTIONS = (SORT_ASCENDING, SORT_DESCENDING)

logger = logging.getLogger(__name__)


class RepoUnitAssociationManager(object):
    """
    Manager used to handle the associations between repositories and content
    units. The functionality provided within assumes the repo and units have
    been created outside of this manager.
    """

    def associate_unit_by_id(self, repo_id, unit_type_id, unit_id, owner_type,
                             owner_id, update_unit_count=True):
        """
        Creates an association between the given repository and content unit.

        If there is already an association between the given repo and content
        unit where all other metadata matches the input to this method,
        this call has no effect.

        Both repo and unit must exist in the database prior to this call,
        however this call will not verify that for performance reasons. Care
        should be taken by the caller to preserve the data integrity.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being added
        @type  unit_type_id: str

        @param unit_id: uniquely identifies the unit within the given type
        @type  unit_id: str

        @param owner_type: category of the caller making the association;
                           must be one of the OWNER_* variables in this module
        @type  owner_type: str

        @param owner_id: identifies the caller making the association, either
                         the importer ID or user login
        @type  owner_id: str

        @param update_unit_count: if True, updates the unit association count
                                  after the new association is made. Set this
                                  to False when doing bulk associations, and
                                  make one call to update the count at the end.
                                  defaults to True
        @type  update_unit_count: bool

        @raise InvalidType: if the given owner type is not of the valid enumeration
        """

        if owner_type not in _OWNER_TYPES:
            raise exceptions.InvalidValue(['owner_type'])

        # If the association already exists, no need to do anything else
        spec = {'repo_id': repo_id,
                'unit_id': unit_id,
                'unit_type_id': unit_type_id,
                'owner_type': owner_type,
                'owner_id': owner_id, }
        existing_association = RepoContentUnit.get_collection().find_one(spec)
        if existing_association is not None:
            return

        similar_exists = False
        if update_unit_count:
            similar_exists = RepoUnitAssociationManager.association_exists(repo_id, unit_id,
                                                                           unit_type_id)

        # Create the database entry
        association = RepoContentUnit(repo_id, unit_id, unit_type_id, owner_type, owner_id)
        RepoContentUnit.get_collection().save(association, safe=True)

        # update the count of associated units on the repo object
        if update_unit_count and not similar_exists:
            manager = manager_factory.repo_manager()
            manager.update_unit_count(repo_id, unit_type_id, 1)

    def associate_all_by_ids(self, repo_id, unit_type_id, unit_id_list, owner_type, owner_id):
        """
        Creates multiple associations between the given repo and content units.

        See associate_unit_by_id for semantics.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being added
        @type  unit_type_id: str

        @param unit_id_list: list or generator of unique identifiers for units within the given type
        @type  unit_id_list: list or generator of str

        @param owner_type: category of the caller making the association;
                           must be one of the OWNER_* variables in this module
        @type  owner_type: str

        @param owner_id: identifies the caller making the association, either
                         the importer ID or user login
        @type  owner_id: str

        :return:    number of new units added to the repo
        :rtype:     int

        @raise InvalidType: if the given owner type is not of the valid enumeration
        """

        # There may be a way to batch this in mongo which would be ideal for a
        # bulk operation like this. But for deadline purposes, this call will
        # simply loop and call the single method.

        unique_count = 0
        for unit_id in unit_id_list:
            if not RepoUnitAssociationManager.association_exists(repo_id, unit_id, unit_type_id):
                unique_count += 1
            self.associate_unit_by_id(repo_id, unit_type_id, unit_id, owner_type, owner_id, False)

        # update the count of associated units on the repo object
        if unique_count:
            manager_factory.repo_manager().update_unit_count(
                repo_id, unit_type_id, unique_count)
        return unique_count

    @staticmethod
    def associate_from_repo(source_repo_id, dest_repo_id, criteria=None,
                            import_config_override=None):
        """
        Creates associations in a repository based on the contents of a source
        repository. Units from the source repository can be filtered by
        specifying a criteria object.

        The destination repository must have an importer that can support
        the types of units being associated. This is done by analyzing the
        unit list and the importer metadata and takes place before the
        destination repository is called.

        Pulp does not actually perform the associations as part of this call.
        The unit list is determined and passed to the destination repository's
        importer. It is the job of the importer to make the associate calls
        back into Pulp where applicable.

        If criteria is None, the effect of this call is to copy the source
        repository's associations into the destination repository.

        :param source_repo_id:         identifies the source repository
        :type  source_repo_id:         str
        :param dest_repo_id:           identifies the destination repository
        :type  dest_repo_id:           str
        :param criteria:               optional; if specified, will filter the units retrieved from
                                       the source repository
        :type  criteria:               UnitAssociationCriteria
        :param import_config_override: optional config containing values to use for this import only
        :type  import_config_override: dict
        :return:                       dict with key 'units_successful' whose
                                       value is a list of unit keys that were copied.
                                       units that were associated by this operation
        :rtype:                        dict
        :raise MissingResource:        if either of the specified repositories don't exist
        """
        # Validation
        repo_query_manager = manager_factory.repo_query_manager()
        importer_manager = manager_factory.repo_importer_manager()

        source_repo = repo_query_manager.get_repository(source_repo_id)
        dest_repo = repo_query_manager.get_repository(dest_repo_id)

        # This will raise MissingResource if there isn't one, which is the
        # behavior we want this method to exhibit, so just let it bubble up.
        dest_repo_importer = importer_manager.get_importer(dest_repo_id)
        source_repo_importer = importer_manager.get_importer(source_repo_id)

        # The docs are incorrect on the list_importer_types call; it actually
        # returns a dict with the types under key "types" for some reason.
        supported_type_ids = plugin_api.list_importer_types(
            dest_repo_importer['importer_type_id'])['types']

        # If criteria is specified, retrieve the list of units now
        associate_us = None
        if criteria is not None:
            associate_us = load_associated_units(source_repo_id, criteria)

            # If units were supposed to be filtered but none matched, we're done
            if len(associate_us) == 0:
                # Return an empty list to indicate nothing was copied
                return {'units_successful': []}

        # Now we can make sure the destination repository's importer is capable
        # of importing either the selected units or all of the units
        associated_unit_type_ids = calculate_associated_type_ids(source_repo_id, associate_us)
        unsupported_types = [t for t in associated_unit_type_ids if t not in supported_type_ids]

        if len(unsupported_types) > 0:
            raise exceptions.InvalidValue(['types'])

        # Convert all of the units into the plugin standard representation if
        # a filter was specified
        transfer_units = None
        if associate_us is not None:
            transfer_units = create_transfer_units(associate_us, associated_unit_type_ids)

        # Convert the two repos into the plugin API model
        transfer_dest_repo = common_utils.to_transfer_repo(dest_repo)
        transfer_dest_repo.working_dir = common_utils.importer_working_dir(
            dest_repo_importer['importer_type_id'], dest_repo['id'], mkdir=True)

        transfer_source_repo = common_utils.to_transfer_repo(source_repo)
        transfer_source_repo.working_dir = common_utils.importer_working_dir(
            source_repo_importer['importer_type_id'], source_repo['id'], mkdir=True)

        # Invoke the importer
        importer_instance, plugin_config = plugin_api.get_importer_by_id(
            dest_repo_importer['importer_type_id'])

        call_config = PluginCallConfiguration(plugin_config, dest_repo_importer['config'],
                                              import_config_override)
        login = manager_factory.principal_manager().get_principal()['login']
        conduit = ImportUnitConduit(
            source_repo_id, dest_repo_id, source_repo_importer['id'], dest_repo_importer['id'],
            RepoContentUnit.OWNER_TYPE_USER, login)

        try:
            copied_units = importer_instance.import_units(
                transfer_source_repo, transfer_dest_repo, conduit, call_config,
                units=transfer_units)
            unit_ids = [u.to_id_dict() for u in copied_units]
            return {'units_successful': unit_ids}

        except Exception:
            msg = _('Exception from importer [%(i)s] while importing units into repository [%(r)s]')
            msg = msg % {'i': dest_repo_importer['importer_type_id'], 'r': dest_repo_id}
            logger.exception(msg)
            raise exceptions.PulpExecutionException(), None, sys.exc_info()[2]

    def unassociate_unit_by_id(self, repo_id, unit_type_id, unit_id, owner_type, owner_id,
                               notify_plugins=True):
        """
        Removes the association between a repo and the given unit. Only the
        association made by the given owner will be removed. It is possible the
        repo will still have a manually created association will for the unit.

        If no association exists between the repo and unit, this call has no
        effect.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being removed
        @type  unit_type_id: str

        @param unit_id: uniquely identifies the unit within the given type
        @type  unit_id: str

        @param owner_type: category of the caller who created the association;
                           must be one of the OWNER_* variables in this module
        @type  owner_type: str

        @param owner_id: identifies the caller who created the association, either
                         the importer ID or user login
        @type  owner_id: str

        @param notify_plugins: if true, relevant plugins will be informed of the
               removal
        @type  notify_plugins: bool
        """
        return self.unassociate_all_by_ids(repo_id, unit_type_id, [unit_id], owner_type, owner_id,
                                           notify_plugins=notify_plugins)

    def unassociate_all_by_ids(self, repo_id, unit_type_id, unit_id_list, owner_type, owner_id,
                               notify_plugins=True):
        """
        Removes the association between a repo and a number of units. Only the
        association made by the given owner will be removed. It is possible the
        repo will still have a manually created association will for the unit.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of units being removed
        @type  unit_type_id: str

        @param unit_id_list: list of unique identifiers for units within the given type
        @type  unit_id_list: list of str

        @param owner_type: category of the caller who created the association;
                           must be one of the OWNER_* variables in this module
        @type  owner_type: str

        @param owner_id: identifies the caller who created the association, either
                         the importer ID or user login
        @type  owner_id: str

        @param notify_plugins: if true, relevant plugins will be informed of the
               removal
        @type  notify_plugins: bool
        """
        association_filters = {'unit_id': {'$in': unit_id_list}}
        criteria = UnitAssociationCriteria(type_ids=[unit_type_id],
                                           association_filters=association_filters)

        return self.unassociate_by_criteria(repo_id, criteria, owner_type, owner_id,
                                            notify_plugins=notify_plugins)

    @staticmethod
    def unassociate_by_criteria(repo_id, criteria, owner_type, owner_id, notify_plugins=True):
        """
        Unassociate units that are matched by the given criteria.

        :param repo_id:        identifies the repo
        :type  repo_id:        str
        :param criteria:
        :param owner_type:     category of the caller who created the association
        :type  owner_type:     str
        :param owner_id:       identifies the call who created the association
        :type  owner_id:       str
        :param notify_plugins: if true, relevant plugins will be informed of the removal
        :type  notify_plugins: bool
        """
        association_query_manager = manager_factory.repo_unit_association_query_manager()
        unassociate_units = association_query_manager.get_units(repo_id, criteria=criteria)

        if len(unassociate_units) == 0:
            return {}

        unit_map = {}  # maps unit_type_id to a list of unit_ids

        for unit in unassociate_units:
            id_list = unit_map.setdefault(unit['unit_type_id'], [])
            id_list.append(unit['unit_id'])

        collection = RepoContentUnit.get_collection()
        repo_manager = manager_factory.repo_manager()

        for unit_type_id, unit_ids in unit_map.items():
            spec = {'repo_id': repo_id,
                    'unit_type_id': unit_type_id,
                    'unit_id': {'$in': unit_ids}
                    }
            collection.remove(spec, safe=True)

            unique_count = sum(
                1 for unit_id in unit_ids if not RepoUnitAssociationManager.association_exists(
                    repo_id, unit_id, unit_type_id))
            if not unique_count:
                continue

            repo_manager.update_unit_count(repo_id, unit_type_id, -unique_count)

        # Convert the units into transfer units. This happens regardless of whether or not
        # the plugin will be notified as it's used to generate the return result,
        unit_type_ids = calculate_associated_type_ids(repo_id, unassociate_units)
        transfer_units = create_transfer_units(unassociate_units, unit_type_ids)

        if notify_plugins:
            remove_from_importer(repo_id, transfer_units)

        # Match the return type/format as copy
        serializable_units = [u.to_id_dict() for u in transfer_units]

        return {'units_successful': serializable_units}

    @staticmethod
    def association_exists(repo_id, unit_id, unit_type_id):
        """
        Determines if an identical association already exists.

        I know the order of arguments does not match other methods in this
        module, but it does match the constructor for the RepoContentUnit
        object, which I think is the higher authority.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being removed
        @type  unit_type_id: str

        @param unit_id: uniquely identifies the unit within the given type
        @type  unit_id: str

        @return: True if unique else False
        @rtype:  bool
        """
        spec = {
            'repo_id': repo_id,
            'unit_id': unit_id,
            'unit_type_id': unit_type_id,
        }
        unit_coll = RepoContentUnit.get_collection()

        existing_count = unit_coll.find(spec).count()
        return bool(existing_count)


associate_from_repo = task(RepoUnitAssociationManager.associate_from_repo, base=Task)
unassociate_by_criteria = task(RepoUnitAssociationManager.unassociate_by_criteria, base=Task)


def load_associated_units(source_repo_id, criteria):
    criteria.association_fields = None

    # Retrieve the units to be associated
    association_query_manager = manager_factory.repo_unit_association_query_manager()
    associate_us = association_query_manager.get_units(source_repo_id, criteria=criteria)

    return associate_us


def calculate_associated_type_ids(source_repo_id, associated_units):
    if associated_units is not None:
        associated_unit_type_ids = set([u['unit_type_id'] for u in associated_units])
    else:
        association_query_manager = manager_factory.repo_unit_association_query_manager()
        associated_unit_type_ids = association_query_manager.unit_type_ids_for_repo(source_repo_id)
    return associated_unit_type_ids


def create_transfer_units(associate_units, associated_unit_type_ids):
    type_defs = {}
    for def_id in associated_unit_type_ids:
        type_def = types_db.type_definition(def_id)
        type_defs[def_id] = type_def

    transfer_units = []
    for unit in associate_units:
        type_id = unit['unit_type_id']
        u = conduit_common_utils.to_plugin_associated_unit(unit, type_defs[type_id])
        transfer_units.append(u)

    return transfer_units


def remove_from_importer(repo_id, transfer_units):
    # Retrieve the repo from the database and convert to the transfer repo
    repo_query_manager = manager_factory.repo_query_manager()
    repo = repo_query_manager.get_repository(repo_id)

    importer_manager = manager_factory.repo_importer_manager()
    repo_importer = importer_manager.get_importer(repo_id)

    transfer_repo = common_utils.to_transfer_repo(repo)
    transfer_repo.working_dir = common_utils.importer_working_dir(repo_importer['importer_type_id'],
                                                                  repo_id, mkdir=True)

    # Retrieve the plugin instance to invoke
    importer_instance, plugin_config = plugin_api.get_importer_by_id(
        repo_importer['importer_type_id'])
    call_config = PluginCallConfiguration(plugin_config, repo_importer['config'])

    # Invoke the importer's remove method
    try:
        importer_instance.remove_units(transfer_repo, transfer_units, call_config)
    except Exception:
        msg = _('Exception from importer [%(i)s] while removing units from repo [%(r)s]')
        msg = msg % {'i': repo_importer['id'], 'r': repo_id}
        logger.exception(msg)

        # Do not raise the exception; this should not block the removal and is
        # intended to be more informational to the plugin rather than a requirement
