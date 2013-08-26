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
from pulp.server.db.model.consumer import Bind, RepoProfileApplicability, UnitProfile
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.repository import Repo
from pulp.server.managers import factory as managers
from pulp.server.managers.consumer.query import ConsumerQueryManager

_LOG = getLogger(__name__)


class ApplicabilityRegenerationManager(object):

    @staticmethod
    def regenerate_applicability_for_consumers(consumer_criteria):
        """
        Regenerate and save applicability data for given updated consumers.

        :param consumer_criteria: The consumer selection criteria
        :type consumer_criteria: dict
        """
        consumer_query_manager = managers.consumer_query_manager()
        bind_manager = managers.consumer_bind_manager()
        consumer_profile_manager = managers.consumer_profile_manager()

        # Process consumer_criteria
        consumer_ids = [c['id'] for c in consumer_query_manager.find_by_criteria(consumer_criteria)]

        for consumer_id in consumer_ids:
            # Get all unit profiles for the consumer
            unit_profiles = consumer_profile_manager.get_profiles(consumer_id)
            # Get all repo ids bound to the consumer
            criteria = Criteria(filters={'consumer_id': consumer_id}, fields=['repo_id'])
            bound_repo_ids = [b['repo_id'] for b in bind_manager.find_by_criteria(criteria)]
            if not bound_repo_ids:
                continue

            # Regenerate applicability for each unit profile that supports applicability
            for unit_profile in unit_profiles:
                ApplicabilityRegenerationManager.regenerate_applicability(unit_profile, 
                                                                          bound_repo_ids, 
                                                                          skip_existing=True)

    @staticmethod
    def regenerate_applicability_for_repos(repo_criteria=None):
        """
        Regenerate and save applicability data affected by given updated repositories.

        :param repo_criteria: The repo selection criteria
        :type repo_criteria: dict
        """
        repo_query_manager = managers.repo_query_manager()
        bind_manager = managers.consumer_bind_manager()
        consumer_profile_manager = managers.consumer_profile_manager()

        # Process repo criteria
        criteria_repo_ids = [r['id'] for r in repo_query_manager.find_by_criteria(repo_criteria)]
        if not criteria_repo_ids:
            return

        # Get consumers bound to given repositories
        criteria = Criteria(filters={'repo_id': {'$in': criteria_repo_ids}}, fields=['consumer_id'])
        consumer_ids = [b['consumer_id'] for b in bind_manager.find_by_criteria(criteria)]
        # Remove duplicate consumer ids
        consumer_ids = list(set(consumer_ids))

        for consumer_id in consumer_ids:
            # Get all unit profiles for the consumer
            unit_profiles = consumer_profile_manager.get_profiles(consumer_id)
            # Get repositories from criteria_repo_ids that are bound to this consumer 
            criteria = Criteria(filters={'repo_id': {'$in': criteria_repo_ids},
                                         'consumer_id': consumer_id},
                                fields=['repo_id'])
            bound_repo_ids = [b['repo_id'] for b in bind_manager.find_by_criteria(criteria)]
            if not bound_repo_ids:
                continue

            # Regenerate applicability for each unit profile that supports applicability
            for unit_profile in unit_profiles:
                ApplicabilityRegenerationManager.regenerate_applicability(unit_profile, 
                                                                          bound_repo_ids, 
                                                                          skip_existing=False)

    @staticmethod
    def regenerate_applicability(unit_profile, bound_repo_ids, skip_existing=True):
        """
        Regenerate and save applicability data for given unit profile and repo ids.

        :param unit_profile: a consumer unit profile
        :type unit_profile: object

        :param bound_repo_ids: repo ids to be used to calculate applicability
                              against the given unit profile
        :type bound_repo_ids: str

        :param skip_existing: flag to indicate whether regeneration should be skipped
                              for existing RepoProfileApplicability objects
        :type skip_existing: boolean
        """
        # Get the profiler for content_type of given unit_profile
        profiler, profiler_cfg = ApplicabilityRegenerationManager.__profiler(unit_profile['content_type'])
        call_config = PluginCallConfiguration(plugin_config=profiler_cfg, repo_plugin_config=None)

        # Check if the profiler supports applicability, else return
        if profiler.calculate_applicable_units == Profiler.calculate_applicable_units:
            # If base class calculate_applicable_units method is called, skip applicability regeneration
            return

        profiler_conduit = ProfilerConduit()

        # Regenerate applicability for each bound repository
        for bound_repo_id in bound_repo_ids:
            existing_applicability = ApplicabilityRegenerationManager._get_existing_applicability(bound_repo_id, 
                                                                                                  unit_profile['profile_hash'])
            if existing_applicability and skip_existing:
                continue

            # Find out which content types have unit counts greater than zero for these bound repos
            repo_content_types = ApplicabilityRegenerationManager._get_existing_repo_content_types(bound_repo_id)
            # Get the intersection of existing types in the repo and the types that the profiler handles. 
            # If the intersection is not empty, regenerate applicability
            if ( set(repo_content_types) & set(profiler.metadata()['types']) ):
                try:
                    applicability = profiler.calculate_applicable_units(unit_profile['profile'],
                                                                        bound_repo_id,
                                                                        call_config,
                                                                        profiler_conduit)
                except NotImplementedError:
                    _LOG.warn("Profiler for content type [%s] does not support applicability" %
                                unit_profile['content_type'])
                    continue

                if existing_applicability:
                    # Update existing applicability object since skip_existing is False
                    existing_applicability.applicability = applicability
                    existing_applicability.save()
                else:
                    # Create a new RepoProfileApplicability object and save it in the db
                    RepoProfileApplicability.objects.create(unit_profile['profile_hash'],
                                                            bound_repo_id,
                                                            unit_profile['profile'],
                                                            applicability)

    @staticmethod
    def _get_existing_repo_content_types(repo_id):
        """
        For the given repo_id, return a list of content_type_ids that have content units counts greater than 0.

        :param repo_id: The repo_id for the repository that we wish to know the unit types contained therein
        :type  repo_id: basestring
        :return:        A list of content type ids that have unit counts greater than 0
        :rtype:         list
        """
        repo_content_types_with_non_zero_unit_count = []
        repo = managers.repo_query_manager().find_by_id(repo_id)
        if repo:
            for content_type, count in repo['content_unit_counts'].items():
                if count > 0:
                    repo_content_types_with_non_zero_unit_count.append(content_type)
        return repo_content_types_with_non_zero_unit_count

    @staticmethod
    def _get_existing_applicability(repo_id, profile_hash):
        """
        Check if applicability for given repo and profle hash is already calculated.
        
        :param repo_id:      repo id
        :type repo_id:       basestring
        :param profile_hash: unit profile hash
        :type profile_hash:  basestring
        :return:             existing RepoProfileApplicability object for given repo id and profile hash or None
        :type:               pulp.server.db.model.consumer.RepoProfileApplicability
        """
        query_params = {'repo_id': repo_id, 'profile_hash': profile_hash}
        try:
            existing_applicability = RepoProfileApplicability.objects.get(query_params)
        except DoesNotExist:
            existing_applicability = None
        return existing_applicability

    @staticmethod
    def __profiler(type_id):
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

    @staticmethod
    def remove_orphans():
        """
        The RepoProfileApplicability objects can become orphaned over time, as repositories are
        deleted, or as consumer profiles change. This method searches for RepoProfileApplicability
        objects that reference either repositories or profile hashes that no longer exist in Pulp.
        """
        # Find all of the repo_ids that are referenced by RepoProfileApplicability objects
        rpa_collection = RepoProfileApplicability.get_collection()
        rpa_repo_ids = rpa_collection.distinct('repo_id')

        # Find all of the repo_ids that exist in Pulp
        repo_ids = Repo.get_collection().distinct('id')

        # Find rpa_repo_ids that aren't part of repo_ids
        missing_repo_ids = list(set(rpa_repo_ids) - set(repo_ids))

        # Remove all RepoProfileApplicability objects that reference these repo_ids
        if missing_repo_ids:
            rpa_collection.remove({'repo_id': {'$in': missing_repo_ids}})

        # Next, we need to find profile_hashes that don't exist in the UnitProfile collection
        rpa_profile_hashes = rpa_collection.distinct('profile_hash')

        # Find the profile hashes that exist in current UnitProfiles
        profile_hashes = UnitProfile.get_collection().distinct('profile_hash')

        # Find profile hashes that we have RepoProfileApplicability objects for, but no real
        # UnitProfiles
        missing_profile_hashes = list(set(rpa_profile_hashes) - set(profile_hashes))

        # Remove all RepoProfileApplicability objects that reference these profile hashes
        if missing_profile_hashes:
            rpa_collection.remove({'profile_hash': {'$in': missing_profile_hashes}})
# Instantiate one of the managers on the object it manages for convenience
RepoProfileApplicability.objects = RepoProfileApplicabilityManager()


def retrieve_consumer_applicability(consumer_criteria, content_types=None):
    """
    Query content applicability for consumers matched by a given consumer_criteria, optionally
    limiting by content type.

    This method returns a list of dictionaries that each have two
    keys: 'consumers', and 'applicability'. 'consumers' will index a list of consumer_ids,
    for consumers that have the same repository bindings and profiles. 'applicability' will
    index a dictionary that will have keys for each content type that is applicable, and the
    content type ids will index the applicability data for those content types. For example,

    [{'consumers': ['consumer_1', 'consumer_2'],
      'applicability': {'content_type_1': ['unit_1', 'unit_3']}},
     {'consumers': ['consumer_2', 'consumer_3'],
      'applicability': {'content_type_1': ['unit_1', 'unit_2']}}]

    :param consumer_ids:  A list of consumer ids that the applicability data should be retrieved
                          against
    :type  consumer_ids:  list
    :param content_types: An optional list of content types that the caller wishes to limit the
                          results to. Defaults to None, which will return data for all types
    :type  content_types: list
    :return: applicability data matching the consumer criteria query
    :rtype:  list
    """
    # We only need the consumer ids
    consumer_criteria['fields'] = ['id']
    consumer_ids = [c['id'] for c in ConsumerQueryManager.find_by_criteria(consumer_criteria)]
    consumer_map = dict([(c, {'profiles': [], 'repo_ids': []}) for c in consumer_ids])

    # Fill out the mapping of consumer_ids to profiles, and store the list of profile_hashes
    profile_hashes = _add_profiles_to_consumer_map_and_get_hashes(consumer_ids, consumer_map)

    # Now add in repo_ids that the consumers are bound to
    _add_repo_ids_to_consumer_map(consumer_ids, consumer_map)
    # We don't need the list of consumer_ids anymore, so let's free a little RAM
    del consumer_ids

    # Now lets get all RepoProfileApplicability objects that have the profile hashes for our
    # consumers
    applicability_map = _get_applicability_map(profile_hashes, content_types)
    # We don't need the profile_hashes anymore, so let's free some RAM
    del profile_hashes

    # Now we need to add consumers who match the applicability data to the applicability_map
    _add_consumers_to_applicability_map(consumer_map, applicability_map)
    # We don't need the consumer_map anymore, so let's free it up
    del consumer_map

    # Collate all the entries for the same sets of consumers together
    consumer_applicability_map = _get_consumer_applicability_map(applicability_map)
    # Free the applicability_map, we don't need it anymore
    del applicability_map

    # Form the data into the expected output format and return
    return _format_report(consumer_applicability_map)


def _add_consumers_to_applicability_map(consumer_map, applicability_map):
    """
    For all consumers in the consumer_map, look for their profiles and repos in the
    applicability_map, and if found, add the consumer_ids to the applicability_map.

    :param consumer_map:      A dictionary mapping consumer_ids to dictionaries with keys
                              'profiles' and 'repo_ids'. 'profiles' indexes a list of profiles
                              for each consumer_id, and 'repo_ids' indexes a list of repo_ids
                              that the consumer is bound to.
    :type  consumer_map:      dict
    :param applicability_map: The mapping of (profile_hash, repo_id) to applicability_data and
                              consumer_ids the data applies to. This method appends
                              consumer_ids to the appropriate lists of consumer_ids
    :type  applicability_map: dict
    """
    for consumer_id, repo_profile_data in consumer_map.items():
        for profile in repo_profile_data['profiles']:
            for repo_id in repo_profile_data['repo_ids']:
                repo_profile = (profile['profile_hash'], repo_id)
                # Only add the consumer to the applicability map if there is applicability_data
                # for this combination of repository and profile
                if repo_profile in applicability_map:
                    applicability_map[repo_profile]['consumers'].append(consumer_id)


def _add_profiles_to_consumer_map_and_get_hashes(consumer_ids, consumer_map):
    """
    Query for all the profiles associated with the given list of consumer_ids, add those
    profiles to the consumer_map, and then return a list of all profile_hashes.

    :param consumer_ids: A list of consumer_ids that we want to map the profiles to
    :type  consumer_ids: list
    :param consumer_map: A dictionary mapping consumer_ids to a dictionary with key 'profiles',
                         which indexes a list that this method will append the found profiles
                         to.
    :type  consumer_map: dict
    :return:             A list of the profile_hashes that were associated with the given
                         consumers
    :rtype:              list
    """
    profiles = UnitProfile.get_collection().find(
        {'consumer_id': {'$in': consumer_ids}},
        fields=['consumer_id', 'profile_hash'])
    profile_hashes = set()
    for p in profiles:
        consumer_map[p['consumer_id']]['profiles'].append(p.to_dict())
        profile_hashes.add(p['profile_hash'])
    # Let's return a list of all the unique profile_hashes for the query we will do a
    # bit later for applicability data
    return list(profile_hashes)


def _add_repo_ids_to_consumer_map(consumer_ids, consumer_map):
    """
    Query for all bindings for the given list of consumer_ids, and for each one add the bound
    repo_ids to the consumer_map's entry for the consumer.

    :param consumer_ids: The list of consumer_ids. We could pull this from the consumer_map,
                         but since we already have this list it's probably more performant to
                         use it as is.
    :type  consumer_ids: list
    :param consumer_map: A dictionary mapping consumer_ids to a dictionary with key 'profiles',
                         which indexes a list that this method will append the found profiles
                         to.
    :type  consumer_map: dict
    """
    bindings = Bind.get_collection().find(
        {'consumer_id': {'$in': consumer_ids}},
        fields=['consumer_id', 'repo_id'])
    for b in bindings:
        consumer_map[b['consumer_id']]['repo_ids'].append(b['repo_id'])


def _format_report(consumer_applicability_map):
    """
    Turn the consumer_applicability_map into the expected response format for this API call.

    :param consumer_applicability_map: A mapping of frozensets of consumers to their
                                       applicability data
    :type  consumer_applicability_map: dict
    :return:                           A list of dictionaries that have two keys, consumers
                                       and applicability. consumers indexes a list of
                                       consumer_ids, and applicability indexes the
                                       applicability data for those consumer_ids.
    :rtype:                            list
    """
    report = []
    for consumers, applicability in consumer_applicability_map.iteritems():
        # If there are no consumers for this applicability data, there is no need to include
        # it in the report
        if consumers:
            applicability_data = {'consumers': list(consumers),
                                  'applicability': applicability}
            report.append(applicability_data)

    return report


def _get_applicability_map(profile_hashes, content_types):
    """
    Build an "applicability_map", which is a dictionary that maps tuples of
    (profile_hash, repo_id) to a dictionary of applicability data and consumer_ids. The
    consumer_ids are just initialized to an empty list, so that a later method can add
    consumers to it. For example, it might look like:

    {('profile_hash_1', 'repo_1'): {'applicability': {<applicability_data>}, 'consumers': []}}

    :param profile_hashes: A list of profile hashes that the applicabilities should be queried
                           with. The applicability map is initialized with all applicability
                           data for all the given profile_hashes.
    :type  profile_hashes: list
    :param content_types:  If not None, content_types is a list of content_types to
                           be included in the applicability data within the
                           applicability_map
    :type  content_types:  list or None
    :return:               The applicability map
    :rtype:                dict
    """
    applicabilities = RepoProfileApplicability.get_collection().find(
        {'profile_hash': {'$in': profile_hashes}},
        fields=['profile_hash', 'repo_id', 'applicability'])
    return_value = {}
    for a in applicabilities:
        if content_types is not None:
            # The caller has requested us to filter by content_type, so we need to look through
            # the applicability data and filter out the unwanted content types. Some
            # applicabilities may end up being empty if they don't have any data for the
            # requested types, so we'll build a list of those to remove
            for key in a['applicability'].keys():
                if key not in content_types:
                    del a['applicability'][key]
            # If a doesn't have anything worth reporting, move on to the next applicability
            if not a['applicability']:
                continue
        return_value[(a['profile_hash'], a['repo_id'])] = {'applicability': a['applicability'],
                                                           'consumers': []}
    return return_value


def _get_consumer_applicability_map(applicability_map):
    """
    Massage the applicability_map into a form that will help us to collate applicability
    groups that contain the same data together.

    :param applicability_map: The mapping of (profile_hash, repo_id) to applicability_data and
                              consumer_ids it applies to. This method appends consumer_ids to
                              the appropriate lists of consumer_ids
    :type  applicability_map: dict
    :return:                  The consumer_applicability_map, which maps frozensets of
                              consumer_ids to their collective applicability data.
    :rtype:                   dict
    """
    consumer_applicability_map = {}
    for repo_profile, data in applicability_map.iteritems():
        # This will be the key for our map, a set of the consumers that share data
        consumers = frozenset(data['consumers'])
        if consumers in consumer_applicability_map:
            for content_type, applicability in data['applicability'].iteritems():
                if content_type in consumer_applicability_map[consumers]:
                    # There is already applicability data for this consumer set and
                    # content type. We will convert the existing data and the new data to
                    # sets, generate the union of those sets, and turn it back into a list
                    # so that we can report unique units.
                    consumer_applicability_map[consumers][content_type] = list(
                        set(consumer_applicability_map[consumers][content_type]) |\
                        set(applicability))
                else:
                    # This consumer set does not already have applicability data for this type, so
                    # let's set applicability as the data for it
                    consumer_applicability_map[consumers][content_type] = applicability
        else:
            # This consumer set is not already part of the consumer_applicability_map, so we can
            # set all the applicability data we have to this consumer set
            consumer_applicability_map[consumers] = data['applicability']
    return consumer_applicability_map
