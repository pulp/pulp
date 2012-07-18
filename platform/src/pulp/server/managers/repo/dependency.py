# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import sys

import pulp.plugins.conduits._common as conduit_common_utils
from   pulp.plugins.conduits.dependency import DependencyResolutionConduit
from   pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
import pulp.plugins.types.database as types_db
from   pulp.server.exceptions import MissingResource, PulpExecutionException
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo._common as common_utils


class DependencyManager(object):

    def resolve_dependencies_by_criteria(self, repo_id, criteria, options):
        """
        Calculates dependencies for units in the given repositories. The
        repository's importer is used to perform the calculation. The units
        to resolve dependencies for are calculated by applying the given
        criteria against the repository.

        @param repo_id: identifies the repository
        @type  repo_id: str

        @param criteria: used to determine which units to resolve dependencies for
        @type  criteria: UnitAssociationCriteria

        @param options: dict of options to pass the importer to drive the resolution
        @type  options: dict

        @return: list of units in SON format
        @rtype:  list
        """
        association_query_manager = manager_factory.repo_unit_association_query_manager()
        units = association_query_manager.get_units(repo_id, criteria=criteria)

        # The bulk of the validation will be done in the chained call below

        return self.resolve_dependencies_by_units(repo_id, units, options)

    def resolve_dependencies_by_units(self, repo_id, units, options):
        """
        Calculates dependencies for the given set of units in the given
        repository.

        @param repo_id: identifies the repository
        @type  repo_id: str

        @param units: list of database representations of units to resolve
               dependencies for
        @type  units: list

        @param options: dict of options to pass the importer to drive the resolution
        @type  options: dict or None

        @return: list of units in SON format
        @rtype:  list

        @raise MissingResource: if the repo does not exist or does not have
               an importer
        """

        # Validation
        repo_query_manager = manager_factory.repo_query_manager()
        importer_manager = manager_factory.repo_importer_manager()

        # The following will raise MissingResource as appropriate
        repo = repo_query_manager.get_repository(repo_id)
        repo_importer = importer_manager.get_importer(repo_id)

        try:
            importer_instance, plugin_config = plugin_api.get_importer_by_id(repo_importer['importer_type_id'])
        except plugin_exceptions.PluginNotFound:
            raise MissingResource(repo_id), None, sys.exc_info()[2]

        # Package for the importer call
        call_config = PluginCallConfiguration(plugin_config, repo_importer['config'], options)
        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.importer_working_dir(repo_importer['importer_type_id'], repo_id, mkdir=True)

        conduit = DependencyResolutionConduit(repo_id, repo_importer['id'])

        # Convert all of the units into the plugin standard representation
        transfer_units = []

        # Preload all the type defs so we don't hammer the database unnecessarily
        type_defs = {}
        all_type_def_ids = set([u['unit_type_id'] for u in units])
        for def_id in all_type_def_ids:
            type_def = types_db.type_definition(def_id)
            type_defs[def_id] = type_def

        for unit in units:
            type_id = unit['unit_type_id']
            u = conduit_common_utils.to_plugin_unit(unit, type_defs[type_id])
            transfer_units.append(u)

        # Invoke the importer
        try:
            transfer_deps = importer_instance.resolve_dependencies(transfer_repo, transfer_units, conduit, call_config)
        except Exception, e:
            raise PulpExecutionException(), None, sys.exc_info()[2]

        # Parse the results back into SON representations of the units

        # Pull out the unit keys and collate them by type
        units_by_type_def = {}
        for t in transfer_deps:
            unit_list = units_by_type_def.setdefault(t.type_id, [])
            unit_list.append(t.unit_key)

        # For each type, retrieve all units by their keys
        content_query_manager = manager_factory.content_query_manager()
        deps = []

        for type_id, keys_list in units_by_type_def.items():
            son_units = content_query_manager.get_multiple_units_by_keys_dicts(type_id, keys_list)
            deps += son_units

        return deps
