import sys

from celery import task

from pulp.plugins.conduits.dependency import DependencyResolutionConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.loader import api as plugin_api, exceptions as plugin_exceptions
from pulp.server.async.tasks import Task
from pulp.server.db import model
from pulp.server.exceptions import MissingResource, PulpExecutionException
import pulp.plugins.conduits._common as conduit_common_utils
import pulp.plugins.types.database as types_db
import pulp.server.managers.factory as manager_factory


class DependencyManager(object):
    @staticmethod
    def resolve_dependencies_by_criteria(repo_id, criteria, options):
        """
        Calculates dependencies for units in the given repositories. The
        repository's importer is used to perform the calculation. The units
        to resolve dependencies for are calculated by applying the given
        criteria against the repository.

        :param repo_id:  identifies the repository
        :type  repo_id:  str
        :param criteria: used to determine which units to resolve dependencies for
        :type  criteria: UnitAssociationCriteria
        :param options:  dict of options to pass the importer to drive the resolution
        :type  options:  dict
        :return:         report from the plugin
        :rtype:          object
        """
        association_query_manager = manager_factory.repo_unit_association_query_manager()
        units = association_query_manager.get_units(repo_id, criteria=criteria)

        # The bulk of the validation will be done in the chained call below
        return DependencyManager.resolve_dependencies_by_units(repo_id, units, options)

    @staticmethod
    def resolve_dependencies_by_units(repo_id, units, options):
        """
        Calculates dependencies for the given set of units in the given
        repository.

        :param repo_id:         identifies the repository
        :type  repo_id:         str
        :param units:           list of database representations of units to resolve dependencies
                                for
        :type  units:           list
        :param options:         dict of options to pass the importer to drive the resolution
        :type  options:         dict or None
        :return:                report from the plugin
        :rtype:                 object
        :raise MissingResource: if the repo does not exist or does not have an importer
        """
        # Validation
        importer_manager = manager_factory.repo_importer_manager()
        repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)
        repo_importer = importer_manager.get_importer(repo_id)

        try:
            importer_instance, plugin_config = plugin_api.get_importer_by_id(
                repo_importer['importer_type_id'])
        except plugin_exceptions.PluginNotFound:
            raise MissingResource(repo_id), None, sys.exc_info()[2]

        # Package for the importer call
        call_config = PluginCallConfiguration(plugin_config, repo_importer['config'], options)
        transfer_repo = repo_obj.to_transfer_repo()

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
            u = conduit_common_utils.to_plugin_associated_unit(unit, type_defs[type_id])
            transfer_units.append(u)

        # Invoke the importer
        try:
            dep_report = importer_instance.resolve_dependencies(transfer_repo, transfer_units,
                                                                conduit, call_config)
        except Exception:
            raise PulpExecutionException(), None, sys.exc_info()[2]

        return dep_report


resolve_dependencies_by_criteria = task(DependencyManager.resolve_dependencies_by_criteria,
                                        base=Task)
