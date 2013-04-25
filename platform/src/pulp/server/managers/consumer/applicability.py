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

"""
Contains content applicability management classes
"""

from pulp.server.managers import factory as managers
from pulp.server.managers.pluginwrapper import PluginWrapper
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.profiler import Profiler
from pulp.plugins.model import Consumer as ProfiledConsumer
from pulp.plugins.types import database as content_types_db
from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.server.exceptions import PulpExecutionException
from pulp.server.db.model.criteria import Criteria, UnitAssociationCriteria
from logging import getLogger
from pulp.plugins.conduits import _common as common_utils

_LOG = getLogger(__name__)


class ApplicabilityManager(object):

    def find_applicable_units(self, consumer_criteria=None, repo_criteria=None, unit_criteria=None, override_config=None):
        """
        Determine and report which of the content units specified by the unit_criteria
        are applicable to consumers specified by the consumer_criteria
        with repos specified by repo_criteria. If consumer_criteria is None,
        all consumers registered to the Pulp server are checked for applicability.
        If repo_criteria is None, all repos bound to the consumer are taken
        into consideration. If unit_criteria contains an empty list for a specific type,
        all units with specific type in the repos bound to the consumer
        are taken into consideration. 

        :param consumer_criteria: The consumer selection criteria.
        :type consumer_criteria: dict

        :param repo_criteria: The repo selection criteria.
        :type repo_criteria: dict

        :param unit_criteria: A dictionary of type_id : unit selection criteria
        :type units: dict
                {<type_id1> : <unit_criteria_for_type_id1>,
                 <type_id2> : <unit_criteria_for_type_id2>}
      
        :param override_config: Additional configuration options to be accepted from user
        :type override_config: dict

        :return: applicability reports dictionary keyed by content type id
        :rtype: dict
        """
        result = {}
        conduit = ProfilerConduit()
        consumer_query_manager = managers.consumer_query_manager()
        bind_manager = managers.consumer_bind_manager()

        # Process Repo Criteria
        if repo_criteria:
            # Get repo ids satisfied by specified repo criteria
            repo_query_manager = managers.repo_query_manager()
            repo_criteria_ids = [r['id'] for r in repo_query_manager.find_by_criteria(repo_criteria)]
            # if repo_criteria is specified and there are no repos satisfying the criteria, return empty result
            if not repo_criteria_ids:
                return result
        else:
            repo_criteria_ids = None

        # Process Consumer Criteria
        if consumer_criteria:
            # Get consumer ids satisfied by specified consumer criteria
            consumer_ids = [c['id'] for c in consumer_query_manager.find_by_criteria(consumer_criteria)]
            # if consumer_criteria is specified and there are no consumers satisfying the criteria, return empty result
            if not consumer_ids:
                return result
        else:
            if repo_criteria_ids:
                # If repo_criteria is specified, get all the consumers bound to the repos
                # satisfied by repo_criteria
                bind_criteria = Criteria(filters={"repo_id": {"$in": repo_criteria_ids}})
                consumer_ids = [b['consumer_id'] for b in bind_manager.find_by_criteria(bind_criteria)]
                # Remove duplicate consumer ids
                consumer_ids = list(set(consumer_ids))
            else:
                # Get all consumer ids registered to the Pulp server
                consumer_ids = [c['id'] for c in consumer_query_manager.find_all()]

        # Process Unit Criteria
        if unit_criteria:
            # If unit_criteria is specified, get unit ids satisfied by the criteria for each content type
            # and save them in a dictionary keyed by the content type
            unit_ids_by_type = {}
            content_query_manager = managers.content_query_manager()
            for type_id, criteria in unit_criteria.items():
                if criteria:
                    criteria_ids = [u['_id'] for u in content_query_manager.find_by_criteria(type_id, criteria)]
                    # If there are no units satisfied by the criteria, skip adding it to the dictionary
                    if criteria_ids:
                        unit_ids_by_type[type_id] = criteria_ids
                else:
                    # If criteria for a content type id is None or empty dictionary, add it to the dictionary
                    # with empty list as a value. This will be interpreted as all units of that specific type
                    unit_ids_by_type[type_id] = []
        else:
            # If unit_criteria is not specified set unit_ids_by_type to None to differentiate between
            # considering all units vs considering 0 units since no units were found satisfying given criteria
            unit_ids_by_type = None

        # Create a dictionary with consumer profile and repo_ids bound to the consumer keyed by consumer id
        consumer_profile_and_repo_ids = {}
        all_relevant_repo_ids = set()
        for consumer_id in consumer_ids:
            # Find repos bound to the consumer in consideration and find an intersection of bound repos to the
            # repos specified by repo_criteria
            consumer_bound_repo_ids = [b['repo_id'] for b in bind_manager.find_by_consumer(consumer_id)]
            consumer_bound_repo_ids = list(set(consumer_bound_repo_ids))
            # If repo_criteria is not specified, use repos bound to the consumer, else take intersection 
            # of repos specified in the criteria and repos bound to the consumer.
            if repo_criteria_ids is None:
                repo_ids = consumer_bound_repo_ids
            else:
                repo_ids = list(set(consumer_bound_repo_ids) & set(repo_criteria_ids))

            if repo_ids:
                # Save all eligible repo ids to get relevant plugin unit keys when unit_criteria is not specified
                all_relevant_repo_ids = (all_relevant_repo_ids | set(repo_ids))
                consumer_profile_and_repo_ids[consumer_id] = {'repo_ids': repo_ids}
                consumer_profile_and_repo_ids[consumer_id]['profiled_consumer'] = self.__profiled_consumer(consumer_id)

        # Get relevant units if unit_criteria is not specified
        units = self.__populate_units(unit_ids_by_type, list(all_relevant_repo_ids))

        if units:
            # Call respective profiler api according to the unit type to check for applicability
            for typeid, unit_ids in units.items():
                # if unit_ids is None or empty, continue to the next type id
                if not unit_ids:
                    continue
                # Find a profiler for each type id and find units applicable using that profiler.
                profiler, cfg = self.__profiler(typeid)
                call_config = PluginCallConfiguration(plugin_config=cfg, repo_plugin_config=None,
                                                      override_config=override_config)
                try:
                    report_list = profiler.find_applicable_units(consumer_profile_and_repo_ids, typeid, unit_ids, call_config, conduit)
                except PulpExecutionException:
                    report_list = None

                if report_list is None:
                    _LOG.warn("Profiler for unit type [%s] is not returning applicability reports" % typeid)
                else:
                    result[typeid] = report_list

        return result


    def __profiler(self, typeid):
        """
        Find the profiler.
        Returns the Profiler base class when not matched.

        :param typeid: The content type ID.
        :type typeid: str

        :return: (profiler, cfg)
        :rtype: tuple
        """
        try:
            plugin, cfg = plugin_api.get_profiler_by_type(typeid)
        except plugin_exceptions.PluginNotFound:
            plugin = Profiler()
            cfg = {}
        return PluginWrapper(plugin), cfg

    def __profiled_consumer(self, id):
        """
        Get a profiler consumer model object.

        :param id: A consumer ID.
        :type id: str

        :return: A populated profiler consumer model object.
        :rtype: L{ProfiledConsumer}
        """
        profiles = {}
        manager = managers.consumer_profile_manager()
        for p in manager.get_profiles(id):
            typeid = p['content_type']
            profile = p['profile']
            profiles[typeid] = profile
        return ProfiledConsumer(id, profiles)

    def __populate_units(self, unit_ids_by_type, repo_ids):
        """
        Parse a dictionary of unit ids keyed by content type id and populate units for each type
        if the criteria is empty.

        :param unit_ids_by_type: dictionary of <content type id> : <list of unit ids>
        :type unit_ids_by_type: dict

        :return: if units are specified, return the corresponding units. If unit_ids_by_type dict
                 is empty, return unit ids corresponging to all units in given repo ids.
                 If unit ids list for a particular unit type is empty, return all unit ids
                 in given repo ids with that unit type.
        :rtype: dict
        """
        repo_unit_association_query_manager = managers.repo_unit_association_query_manager()
        result_units = {}

        if unit_ids_by_type is not None:
            for unit_type_id, unit_ids in unit_ids_by_type.items():
                # Get unit type specific collection
                if not unit_ids:
                    # If unit_list is empty for a unit_type, consider all units of specific type
                    criteria = UnitAssociationCriteria(type_ids=[unit_type_id], association_filters={"repo_id": {"$in": repo_ids}}, unit_fields = ['unit_id'])
                    repo_units = repo_unit_association_query_manager.find_by_criteria(criteria)
                    pulp_unit_ids = [u['unit_id'] for u in repo_units]
                    result_units.setdefault(unit_type_id, []).extend(pulp_unit_ids)
                else:
                    result_units.setdefault(unit_type_id, []).extend(unit_ids)
        else:
            # If units are not specified, consider all units in given repos.
            all_unit_type_ids = content_types_db.all_type_ids()
            for unit_type_id in all_unit_type_ids:
                criteria = UnitAssociationCriteria(type_ids=[unit_type_id], association_filters={"repo_id": {"$in": repo_ids}}, unit_fields = ['unit_id'])
                repo_units = repo_unit_association_query_manager.find_by_criteria(criteria)
                pulp_unit_ids = [u['unit_id'] for u in repo_units]
                result_units.setdefault(unit_type_id, []).extend(pulp_unit_ids)

        return result_units

