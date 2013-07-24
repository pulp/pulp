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
from pulp.plugins.profiler import Profiler
from pulp.server.db.model.consumer import RepoProfileApplicability
from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory as managers

TYPE_RPM_PROFILE = 'rpm'
APPLICABILITY_CONTENT_TYPE_IDS = ['rpm', 'erratum']
YUM_DISTRIBUTOR_ID = 'yum_distributor'

_LOG = getLogger(__name__)


class ApplicabilityRegenerationManager(object):

    def regenerate_applicability_for_consumers(self, consumer_criteria):
        """
        Regenerate and save applicability data for given consumers

        :param consumer_criteria: The consumer selection criteria
        :type consumer_criteria: dict
        """
        consumer_query_manager = managers.consumer_query_manager()
        bind_manager = managers.consumer_bind_manager()
        consumer_profile_manager = managers.consumer_profile_manager()
        profiler_conduit = ProfilerConduit()

        # Process consumer_criteria
        consumer_ids = [c['id'] for c in consumer_query_manager.find_by_criteria(consumer_criteria)]

        for consumer_id in consumer_ids:
            # Get consumer unit profile for supported type
            try:
                unit_profile = consumer_profile_manager.get_profile(consumer_id, TYPE_RPM_PROFILE)
            except MissingResource:
                continue
            # Get repositories bound to the consumer with relevant distributor
            criteria = Criteria(filters={'consumer_id': consumer_id, 'distributor_id': YUM_DISTRIBUTOR_ID},
                                fields=['repo_id'])
            bound_repo_ids = [b['repo_id'] for b in bind_manager.find_by_criteria(criteria)]

            # Calculate applicability for bound repositories
            for bound_repo_id in bound_repo_ids:
                self.regenerate_applicability(unit_profile, bound_repo_id, profiler_conduit, skip_existing=True)

    def regenerate_applicability_for_repos(self, repo_criteria=None):
        """
        Regenerate and save applicability data affected by given repositories

        :param repo_criteria: The repo selection criteria
        :type repo_criteria: dict
        """
        repo_query_manager = managers.repo_query_manager()
        bind_manager = managers.consumer_bind_manager()
        consumer_profile_manager = managers.consumer_profile_manager()
        profiler_conduit = ProfilerConduit()

        # Process repo criteria
        criteria_repo_ids = [r['id'] for r in repo_query_manager.find_by_criteria(repo_criteria)]

        # Get consumers bound to given repositories with relevant distributor
        criteria = Criteria(filters={'repo_id': {'$in': criteria_repo_ids}, 'distributor_id': YUM_DISTRIBUTOR_ID},
                            fields=['consumer_id'])
        consumer_ids = [b['consumer_id'] for b in bind_manager.find_by_criteria(criteria)]

        for consumer_id in consumer_ids:
            # Get consumer unit profile for supported type
            try:
                unit_profile = consumer_profile_manager.get_profile(consumer_id, TYPE_RPM_PROFILE)
            except MissingResource:
                continue
            # Get repositories bound to the consumer with relevant distributor
            criteria = Criteria(filters={'repo_id': {'$in': criteria_repo_ids},
                                         'consumer_id': consumer_id,
                                         'distributor_id': YUM_DISTRIBUTOR_ID},
                                fields=['repo_id'])
            bound_repo_ids = [b['repo_id'] for b in bind_manager.find_by_criteria(criteria)]

            # Calculate applicability for bound repositories and for each supported content type
            for bound_repo_id in bound_repo_ids:
                self.regenerate_applicability(unit_profile, bound_repo_id, profiler_conduit, skip_existing=False)

    def regenerate_applicability(self, unit_profile, bound_repo_id, profiler_conduit, skip_existing=True):
        """
        Regenerate and save applicability data for given unit profile and repo id.

        :param unit_profile: a consumer unit profile
        :type unit_profile: object

        :param bound_repo_id: repo id of a repository to be used to calculate applicability
                              against the given consumer profile
        :type bound_repo_id: str

        :param profiler_conduit: profiler conduit
        :type profiler_conduit: pulp.plugins.conduits.profile.ProfilerConduit

        :param skip_existing: flag to indicate whether regeneration should be skipped
                              for existing RepoProfileApplicability objects
        :type skip_existing: boolean
        """
        query_params = {'repo_id': bound_repo_id, 'profile_hash': unit_profile['profile_hash']}
        try:
            existing_applicability = RepoProfileApplicability.objects.get(query_params)
        except DoesNotExist:
            existing_applicability = None

        if existing_applicability and skip_existing:
            return

        applicability = {}
        for content_type_id in APPLICABILITY_CONTENT_TYPE_IDS:
            profiler, cfg = self.__profiler(content_type_id)
            call_config = PluginCallConfiguration(plugin_config=cfg, repo_plugin_config=None)
            try:
                unit_id_list = profiler.calculate_applicable_units(content_type_id,
                                                                   unit_profile['profile'],
                                                                   bound_repo_id,
                                                                   call_config,
                                                                   profiler_conduit)
            except NotImplementedError:
                _LOG.warn("Profiler for content type [%s] is not returning applicability reports" % content_type_id)
                continue

            applicability[content_type_id] = unit_id_list

        if existing_applicability:
            # Update existing applicability object since skip_existing is False
            existing_applicability.applicability = applicability
            existing_applicability.save()
        else:
            # Create a new RepoProfileApplicability object and save it in the db
            RepoProfileApplicability.objects.create(unit_profile['profile_hash'],
                                                    bound_repo_id,
                                                    unit_profile,
                                                    applicability)

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
        return plugin, cfg


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
