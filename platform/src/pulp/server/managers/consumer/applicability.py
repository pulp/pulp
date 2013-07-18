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

from gettext import gettext as _
from logging import getLogger

from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.loader import api as plugin_api, exceptions as plugin_exceptions
from pulp.plugins.model import Consumer as ProfiledConsumer
from pulp.plugins.profiler import Profiler
from pulp.server.db.model.consumer import RepoProfileApplicability
from pulp.server.exceptions import PulpExecutionException, MissingResource
from pulp.server.managers import factory as managers
from pulp.server.managers.pluginwrapper import PluginWrapper

_LOG = getLogger(__name__)


class ApplicabilityManager(object):

    def calculate_applicable_units(self, consumer_criteria=None):
        """
        Calculate applicable units from bound repositories for given consumers

        :param consumer_criteria: The consumer selection criteria.
        :type consumer_criteria: dict

        :return: applicability report
        :rtype: dict
        """
        consumer_query_manager = managers.consumer_query_manager()
        bind_manager = managers.consumer_bind_manager()
        consumer_profile_manager = managers.consumer_profile_manager()

        # Process Consumer Criteria
        if consumer_criteria:
            # Get consumer ids satisfied by specified consumer criteria
            consumer_ids = [c['id'] for c in consumer_query_manager.find_by_criteria(consumer_criteria)]
        else:
            # Get all consumer ids registered to the Pulp server
            consumer_ids = [c['id'] for c in consumer_query_manager.find_all()]

        result = {}
        for consumer_id in consumer_ids:
            result[consumer_id] = {}
            bound_repo_ids = [b['repo_id'] for b in bind_manager.find_by_consumer(consumer_id)]
            bound_repo_ids = list(set(bound_repo_ids))
            for bound_repo_id in bound_repo_ids:
                unit_type_id = 'rpm'
                try:
                    unit_profile = consumer_profile_manager.get_profile(consumer_id, 'rpm')
                except MissingResource:
                    continue
                profiler, cfg = self.__profiler(unit_type_id)
                call_config = PluginCallConfiguration(plugin_config=cfg, repo_plugin_config=None)
                try:
                    unit_list = profiler.calculate_applicable_units(unit_type_id, unit_profile['profile'], bound_repo_id, call_config, ProfilerConduit())
                except PulpExecutionException:
                    unit_list = None

                if unit_list is None:
                    _LOG.warn("Profiler for content type [%s] is not returning applicability reports" % unit_type_id)
                else:
                    result[consumer_id][bound_repo_id] = unit_list

        return result

    def __profiler(self, type_id):
        """
        Find the profiler.
        Returns the Profiler base class when not matched.

        :param type_id: The content type ID.
        :type type_id: str

        :return: (profiler, cfg)
        :rtype: tuple
        """
        try:
            plugin, cfg = plugin_api.get_profiler_by_type(type_id)
        except plugin_exceptions.PluginNotFound:
            plugin = Profiler()
            cfg = {}
        return PluginWrapper(plugin), cfg

    def __get_consumer_profile(self, consumer_id, type_id):
        """
        Get a profiler consumer model object.

        :param consumer_id: A consumer ID.
        :type consumer_id: str

        :return: Consumer unit profile for given type
        :rtype: dict
        """
        profiles = {}
        manager = managers.consumer_profile_manager()
        for p in manager.get_profiles(id):
            typeid = p['content_type']
            profile = p['profile']
            profiles[typeid] = profile
        return ProfiledConsumer(id, profiles)


class DoesNotExist(Exception):
    """
    An Exception to be raised when a get() is called on a manager with query parameters that do not
    match an object in the database.
    """
    pass


class MultipleObjectsReturned(Exception):
    """
    An Exception to be raised when a get() is called on a manager that results in more than one
    object being returned.
    """
    pass


class RepoProfileApplicabilityManager(object):
    """
    This class is useful for querying for RepoProfileApplicability objects in the database.
    """
    def create(self, profile_hash, repo_id, profile, applicability):
        """
        Create and return a RepoProfileApplicability object.

        :param profile_hash:  The hash of the profile that this object contains applicability data
                              for
        :type  profile_hash:  basestring
        :param repo_id:       The repo ID that this applicability data is for
        :type  repo_id:       basestring
        :param profile:       The entire profile that resulted in the profile_hash
        :type  profile:       object
        :param applicability: A dictionary structure mapping unit type IDs to lists of applicable
                              Unit IDs.
        :type  applicability: dict
        :return:              A new RepoProfileApplicability object
        :rtype:               pulp.server.db.model.consumer.RepoProfileApplicability
        """
        applicability = RepoProfileApplicability(
            profile_hash=profile_hash, repo_id=repo_id, profile=profile,
            applicability=applicability)
        applicability.save()
        return applicability

    def filter(self, query_params):
        """
        Get a list of RepoProfileApplicability objects with the given MongoDB query dict.

        :param query_params: A MongoDB query dictionary that selects RepoProfileApplicability
                             documents
        :type  query_params: dict
        :return:             A list of RepoProfileApplicability objects that match the given query
        :rtype:              list
        """
        collection = RepoProfileApplicability.get_collection()
        mongo_applicabilities = collection.find(query_params)
        applicabilities = [RepoProfileApplicability(**dict(applicability)) \
                           for applicability in mongo_applicabilities]
        return applicabilities

    def get(self, query_params):
        """
        Get a single RepoProfileApplicability object with the given MongoDB query dict. This
        will raise a DoesNotExist if no such object exists. It will also raise
        MultipleObjectsReturned if the query_dict was not specific enough to match just one
        RepoProfileApplicability object.

        :param query_params: A MongoDB query dictionary that selects a single
                             RepoProfileApplicability document
        :type  query_params: dict
        :return:             A RepoProfileApplicability object that matches the given query
        :rtype:              pulp.server.db.model.consumer.RepoProfileApplicability
        """
        applicability = self.filter(query_params)
        if not applicability:
            raise DoesNotExist(_('The RepoProfileApplicability object does not exist.'))
        if len(applicability) > 1:
            error_message = _('The given query matched %(num)s documents.')
            error_message = error_message % {'num': len(applicability)}
            raise MultipleObjectsReturned(error_message)
        return applicability[0]
# Instantiate one of the managers on the object it manages for convenience
RepoProfileApplicability.objects = RepoProfileApplicabilityManager()
