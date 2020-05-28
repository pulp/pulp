"""
Contains content applicability management classes
"""
import hashlib
import itertools
import json

from gettext import gettext as _
from logging import getLogger
from uuid import uuid4

from celery import task
from mongoengine import errors as mongo_errors
from pymongo.errors import DuplicateKeyError

from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.loader import api as plugin_api, exceptions as plugin_exceptions
from pulp.plugins.profiler import Profiler
from pulp.server.async.tasks import Task
from pulp.server.db import model, connection
from pulp.server.db.model.consumer import Bind, RepoProfileApplicability, UnitProfile
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers import factory as managers
from pulp.server.managers.consumer.query import ConsumerQueryManager


_logger = getLogger(__name__)


class ApplicabilityRegenerationManager(object):
    @staticmethod
    def regenerate_applicability_for_consumers(consumer_criteria):
        """
        Regenerate and save applicability data for given updated consumers.

        :param consumer_criteria: The consumer selection criteria
        :type consumer_criteria: dict
        """
        consumer_criteria = Criteria.from_dict(consumer_criteria)
        consumer_query_manager = managers.consumer_query_manager()

        # Process consumer_criteria and get all the consumer ids satisfied by the criteria
        consumer_criteria.fields = ['id']
        consumer_ids = [c['id'] for c in consumer_query_manager.find_by_criteria(consumer_criteria)]

        # Following logic of checking existing applicability and getting required data
        # to generate applicability is a bit more complicated than what it could be 'by design'.
        # It is to optimize the number of db queries and improving applicability generation
        # performance. Please consider the implications for applicability generation time
        # when making any modifications to this code.

        consumer_profile_map = ApplicabilityRegenerationManager._get_consumer_profile_map(
            consumer_ids)

        repo_consumer_map = ApplicabilityRegenerationManager._get_repo_consumer_map(
            consumer_ids=consumer_ids)

        # Since there could be different types of profiles and they are related (at the moment
        # these are RPMs and Modulemds in the RPM plugin), it's important to calculate applicability
        # not per profile but for a combination of all profiles of one consumer,
        # all_profiles_hash identifies that set of profiles.

        # Iterate through each unique all_profiles_hash and regenerate applicability,
        # if it doesn't exist.
        for repo_id in repo_consumer_map:
            seen_hashes = set()
            for consumer_id in repo_consumer_map[repo_id]:
                if consumer_id in consumer_profile_map:
                    all_profiles_hash = consumer_profile_map[consumer_id]['all_profiles_hash']
                    if all_profiles_hash in seen_hashes:
                        continue
                    profiles = consumer_profile_map[consumer_id]['profiles']
                    seen_hashes.add(all_profiles_hash)
                    if ApplicabilityRegenerationManager._is_existing_applicability(
                            repo_id, all_profiles_hash):
                        continue
                    # If applicability does not exist, generate applicability data for given
                    # profiles and repo id.
                    ApplicabilityRegenerationManager.regenerate_applicability(all_profiles_hash,
                                                                              profiles, repo_id)

    @staticmethod
    def regenerate_applicability_for_repos(repo_criteria):
        """
        Regenerate and save applicability data affected by given updated repositories.

        :param repo_criteria: The repo selection criteria
        :type repo_criteria: dict
        """
        repo_criteria = Criteria.from_dict(repo_criteria)
        # Process repo criteria
        repo_criteria.fields = ['id']
        repo_ids = [r.repo_id for r in model.Repository.objects.find_by_criteria(repo_criteria)]

        repo_consumer_map = ApplicabilityRegenerationManager._get_repo_consumer_map(
            repo_ids=repo_ids)

        consumer_ids = itertools.chain(*repo_consumer_map.values())
        consumer_profile_map = ApplicabilityRegenerationManager._get_consumer_profile_map(
            consumer_ids)

        for repo_id in repo_consumer_map:
            seen_hashes = set()
            for consumer_id in repo_consumer_map[repo_id]:
                if consumer_id in consumer_profile_map:
                    all_profiles_hash = consumer_profile_map[consumer_id]['all_profiles_hash']
                    if all_profiles_hash in seen_hashes:
                        continue
                    seen_hashes.add(all_profiles_hash)
                    profiles = consumer_profile_map[consumer_id]['profiles']

                    # Regenerate applicability data for a given all_profiles_hash and repo id
                    ApplicabilityRegenerationManager.regenerate_applicability(
                        all_profiles_hash, profiles, repo_id)

    @staticmethod
    def queue_regenerate_applicability_for_repos(repo_criteria):
        """
        Queue a group of tasks to generate and save applicability data affected by given updated
        repositories.

        :param repo_criteria: The repo selection criteria
        :type repo_criteria: dict
        """
        repo_criteria = Criteria.from_dict(repo_criteria)
        # Process repo criteria
        repo_criteria.fields = ['id']
        repo_ids = [r.repo_id for r in model.Repository.objects.find_by_criteria(repo_criteria)]

        repo_consumer_map = ApplicabilityRegenerationManager._get_repo_consumer_map(
            repo_ids=repo_ids)

        consumer_ids = itertools.chain(*repo_consumer_map.values())
        consumer_profile_map = ApplicabilityRegenerationManager._get_consumer_profile_map(
            consumer_ids)

        task_group_id = uuid4()
        batch_size = 10

        # list of tuples (repo_id, all_profiles_hash, profiles)
        profiles_to_process = []
        for repo_id in repo_consumer_map:
            seen_hashes = set()
            for consumer_id in repo_consumer_map[repo_id]:
                if consumer_id in consumer_profile_map:
                    all_profiles_hash = consumer_profile_map[consumer_id]['all_profiles_hash']
                    if all_profiles_hash in seen_hashes:
                        continue
                    seen_hashes.add(all_profiles_hash)
                    profiles = consumer_profile_map[consumer_id]['profiles']
                    if len(profiles_to_process) < batch_size:
                        profiles_to_process.append((repo_id, all_profiles_hash, profiles))
                    else:
                        batch_regenerate_applicability_task.apply_async(
                            (profiles_to_process,), **{'group_id': task_group_id})
                        profiles_to_process = []

        # last few non-processed profiles which didn't make a whole batch
        if profiles_to_process:
            batch_regenerate_applicability_task.apply_async(
                (profiles_to_process,), **{'group_id': task_group_id})
        return task_group_id

    @staticmethod
    def batch_regenerate_applicability(profiles_to_process):
        """
        Regenerate and save applicability data for a batch of applicabilities

        :param profiles_to_process: profile data necessary for applicability calculation,
                                    [(repo_id, all_profiles_hash, profiles), ...]
        :type  profiles_to_process: list of tuples
        """
        for repo_id, all_profiles_hash, profiles in profiles_to_process:

            # Regenerate applicability data for given profiles and repo id
            ApplicabilityRegenerationManager.regenerate_applicability(all_profiles_hash,
                                                                      profiles, repo_id)

    @staticmethod
    def regenerate_applicability(all_profiles_hash, profiles, bound_repo_id):
        """
        Regenerate and save applicability data for given set of profiles and bound repo id.

        :param all_profiles_hash: hash of the consumer profiles
        :type  all_profiles_hash: basestring

        :param profiles: profiles data: (profile_hash, content_type, profile_id)
        :type  profiles: list of tuples

        :param bound_repo_id: repo id to be used to calculate applicability
                              against the given unit profile
        :type  bound_repo_id: str
        """
        profiler_conduit = ProfilerConduit()

        # Get the profiler for content_type of given profiles.
        # The assumption is that the same profiler is used for all the content types, so different
        # profilers are not supported at the moment.
        # Take the content type from the first profile.
        content_type = profiles[0][1]
        profiler, profiler_cfg = ApplicabilityRegenerationManager._profiler(content_type)

        # Check if the profiler supports applicability, else return
        if profiler.calculate_applicable_units == Profiler.calculate_applicable_units:
            # If base class calculate_applicable_units method is called,
            # skip applicability regeneration
            return

        # Find out which content types have unit counts greater than zero in the bound repo
        repo_content_types = ApplicabilityRegenerationManager._get_existing_repo_content_types(
            bound_repo_id)

        # Get the intersection of existing types in the repo and the types that the profiler
        # handles. If the intersection is not empty, regenerate applicability
        if (set(repo_content_types) & set(profiler.metadata()['types'])):
            profile_ids = [p_id for _, _, p_id in profiles]
            unit_profiles = UnitProfile.get_collection().find({'id': {'$in': profile_ids}},
                                                              projection=['profile',
                                                                          'content_type',
                                                                          'profile_hash'])
            try:
                profiles = [(p['profile_hash'], p['content_type'], p['profile']) for p in
                            unit_profiles]
            except TypeError:
                # It means that p = None.
                # Consumer can be removed during applicability regeneration,
                # so it is possible that its profile no longer exists. It is harmless.
                return

            call_config = PluginCallConfiguration(plugin_config=profiler_cfg,
                                                  repo_plugin_config=None)
            try:
                applicability = profiler.calculate_applicable_units(profiles,
                                                                    bound_repo_id,
                                                                    call_config,
                                                                    profiler_conduit)
            except NotImplementedError:
                msg = "Profiler for content type [%s] does not support applicability" % content_type
                _logger.debug(msg)
                return

            # Save applicability results on each of the profiles. The results are duplicated.
            # It's a compromise to have applicability data available in any applicability profile
            # record in the DB.
            for profile in profiles:
                profile_hash = profile[0]
                try:
                    # Create a new RepoProfileApplicability object and save it in the db
                    RepoProfileApplicability.objects.create(profile_hash=profile_hash,
                                                            repo_id=bound_repo_id,
                                                            # profiles can be large, the one in
                                                            # repo_profile_applicability collection
                                                            # is no longer used,
                                                            # it's a duplicated data
                                                            # from the consumer_unit_profiles
                                                            # collection.
                                                            profile=[],
                                                            applicability=applicability,
                                                            all_profiles_hash=all_profiles_hash)
                except DuplicateKeyError:
                    applicability_dict = RepoProfileApplicability.get_collection().find_one(
                        {'repo_id': bound_repo_id, 'all_profiles_hash': all_profiles_hash,
                         'profile_hash': profile_hash})
                    existing_applicability = RepoProfileApplicability(**applicability_dict)
                    existing_applicability.applicability = applicability
                    existing_applicability.save()

    @staticmethod
    def _get_existing_repo_content_types(repo_id):
        """
        For the given repo_id, return a list of content_type_ids that have content units counts
        greater than 0.

        :param repo_id: The repo_id for the repository that we wish to know the unit types contained
                        therein
        :type  repo_id: basestring
        :return:        A list of content type ids that have unit counts greater than 0
        :rtype:         list
        """
        try:
            repo_obj = model.Repository.objects.get(repo_id=repo_id)
        except mongo_errors.DoesNotExist:
            return []

        repo_content_types_with_non_zero_unit_count = []
        for content_type, count in repo_obj.content_unit_counts.items():
            if count > 0:
                repo_content_types_with_non_zero_unit_count.append(content_type)
        return repo_content_types_with_non_zero_unit_count

    @staticmethod
    def _is_existing_applicability(repo_id, all_profiles_hash):
        """
        Check if applicability for given repo and profile hash is already calculated.

        :param repo_id:      repo id
        :type repo_id:       basestring
        :param all_profiles_hash: consumer profiles' hash
        :type all_profiles_hash:  basestring
        :return:             true if applicability exists, false otherwise
        :type:               boolean
        """
        query_params = {'repo_id': repo_id, 'all_profiles_hash': all_profiles_hash}
        if RepoProfileApplicability.get_collection().find(query_params, projection=['_id']).count():
            return True
        return False

    @staticmethod
    def _profiler(type_id):
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

    @staticmethod
    def _get_consumer_profile_map(consumer_ids):
        """
        Create a consumer-profile map:
        {consumer id:
            {'profiles': list of tuples with profile details,
             'all_profiles_hash': hash of all consumer's profile_hashes}}

        :param consumer_ids: consumers for which applicability needs to be regenerated
        :type  consumer_ids: list

        :return: consumer-profile map described above
        :rtype: dict
        """
        consumer_profile_manager = managers.consumer_profile_manager()
        consumer_ids = list(set(consumer_ids))

        # Get all unit profiles associated with given consumers
        unit_profile_criteria = Criteria(
            filters={'consumer_id': {'$in': consumer_ids}, 'profile': {'$ne': []}},
            fields=['consumer_id', 'profile_hash', 'content_type', 'id'])
        all_unit_profiles = consumer_profile_manager.find_by_criteria(unit_profile_criteria)

        consumer_profiles_map = {}

        for unit_profile in all_unit_profiles:
            profile_hash = unit_profile['profile_hash']
            content_type = unit_profile['content_type']
            consumer_id = unit_profile['consumer_id']
            profile_id = unit_profile['id']

            profile_tuple = (profile_hash, content_type, profile_id)
            # Add this tuple to the list of profile tuples for a consumer
            consumer_profiles_map.setdefault(consumer_id, {})
            consumer_profiles_map[consumer_id].setdefault('profiles', []).append(profile_tuple)

        # Calculate and add all_profiles_hash to the map
        for consumer_id, pdata in consumer_profiles_map.items():
            profile_hashes = [pr_hash for pr_hash, _, _ in pdata['profiles']]
            all_profiles_hash = _calculate_all_profiles_hash(profile_hashes)
            consumer_profiles_map[consumer_id]['all_profiles_hash'] = all_profiles_hash

        return consumer_profiles_map

    @staticmethod
    def _get_repo_consumer_map(consumer_ids=[], repo_ids=[]):
        """
        Create a repo-consumer map:
        {repo_id: [consumer_id1, consumer_id2,...]

        Data can be limited to specific consumers or to specific repos.

        :param consumer_ids: consumers which should be included
        :type  consumer_ids: list
        :param repo_ids: repositories which should be included
        :type  repo_ids: list

        :return: repo-consumer map described above
        :rtype: dict
        """
        bind_manager = managers.consumer_bind_manager()

        filters = {}
        if consumer_ids:
            filters = {'consumer_id': {'$in': consumer_ids}}
        elif repo_ids:
            filters = {'repo_id': {'$in': repo_ids}}

        bind_criteria = Criteria(filters=filters,
                                 fields=['repo_id', 'consumer_id'])
        all_repo_bindings = bind_manager.find_by_criteria(bind_criteria)

        repo_consumers_map = {}
        for binding in all_repo_bindings:
            repo_consumers_map.setdefault(binding['repo_id'], []).append(binding['consumer_id'])

        return repo_consumers_map


regenerate_applicability_for_consumers = task(
    ApplicabilityRegenerationManager.regenerate_applicability_for_consumers, base=Task,
    ignore_result=True)
regenerate_applicability_for_repos = task(
    ApplicabilityRegenerationManager.regenerate_applicability_for_repos, base=Task,
    ignore_result=True)
batch_regenerate_applicability_task = task(
    ApplicabilityRegenerationManager.batch_regenerate_applicability, base=Task,
    ignore_results=True)


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
    def create(self, profile_hash, repo_id, profile, applicability, all_profiles_hash):
        """
        Create and return a RepoProfileApplicability object.

        :param profile_hash:  The hash of the profile that is a part of the profile set of a
                              consumer
        :type  profile_hash:  basestring
        :param repo_id:       The repo ID that this applicability data is for
        :type  repo_id:       basestring
        :param profile:       The entire profile that resulted in the profile_hash
        :type  profile:       object
        :param applicability: A dictionary structure mapping unit type IDs to lists of applicable
                              Unit IDs.
        :type  applicability: dict
        :param all_profiles_hash: The hash of the set of the profiles that this applicability
                                  data is for
        :type  all_profiles_hash: basestring
        :return:              A new RepoProfileApplicability object
        :rtype:               pulp.server.db.model.consumer.RepoProfileApplicability
        """
        applicability = RepoProfileApplicability(
            profile_hash=profile_hash, repo_id=repo_id, profile=profile,
            applicability=applicability, all_profiles_hash=all_profiles_hash)
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
        applicabilities = [RepoProfileApplicability(**dict(applicability))
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
        repo_ids = model.Repository.objects.distinct('repo_id')

        # Find rpa_repo_ids that aren't part of repo_ids
        missing_repo_ids = list(set(rpa_repo_ids) - set(repo_ids))

        # Remove all RepoProfileApplicability objects that reference these repo_ids
        if missing_repo_ids:
            rpa_collection.remove({'repo_id': {'$in': missing_repo_ids}})

        # The code below has to be compatible with MongoDB 2.6+, it has to workaround
        # the 16MB BSON size limit, and no race conditions should be introduced.
        # For those reasons it may look complicated or unintuitive, but it does the following:
        #
        #     active_profile_hashes = set(consumer_unit_profile collection)
        #     profile_hashes_in_applicability = set(repo_profile_applicability collection)
        #     orphaned_profile_hashes = profile_hashes_in_applicability - active_profile_hashes
        #     for batch in paginate(orphaned_profile_hashes):
        #          remove_from_applicability_collection(where profile_hashes in batch)
        #

        # Find the profile hashes that exist in current UnitProfiles
        unit_profile_coll = UnitProfile.get_collection()
        active_profile_hashes = unit_profile_coll.distinct('profile_hash')

        # Find if there are any empty consumer profiles, remove them from the active ones because
        # applicability for those is not needed. Max is one profile per content type.
        empty_profile_hashes = unit_profile_coll.find({'profile': []}, projection=['profile_hash'])
        for empty_profile in empty_profile_hashes:
            empty_profile_hash = empty_profile['profile_hash']
            if empty_profile_hash in active_profile_hashes:
                active_profile_hashes.remove(empty_profile_hash)

        # Define a group stage for aggregation to find the profile hashes
        # that are present in RepoProfileApplicability collection
        group_stage = {'$group':
                       {'_id': None,
                        'rpa_profiles': {'$addToSet': '$profile_hash'}}}

        # Define a project stage to find orphaned profile hashes in the RepoProfileApplicability
        project_stage1 = {"$project":
                          {"orphaned_profiles":
                           {"$setDifference": ["$rpa_profiles", active_profile_hashes]}}}

        # Unwind the array of results so each element becomes a document itself.
        # It's important if results are huge (>16MB)
        unwind_stage = {"$unwind": "$orphaned_profiles"}

        # Reshape results in a way that no indices are violated: _id = profile_hash
        project_stage2 = {"$project": {"_id": "$orphaned_profiles"}}

        # Write results to a separate collection.
        # If a collection exists, old data is substituted with a new one.
        out_stage = {"$out": "orphaned_profile_hash"}

        # Trigger aggregation pipeline
        rpa_collection.aggregate([group_stage,
                                  project_stage1,
                                  unwind_stage,
                                  project_stage2,
                                  out_stage], allowDiskUse=True)

        # Remove orphaned applicability profiles using profile hashes from the temporary collection.
        # Prepare a list of profiles to remove them in batches in case there are millions of them.
        orphaned_profiles_collection = connection.get_collection('orphaned_profile_hash')
        profiles_batch_size = 100000
        profiles_total = orphaned_profiles_collection.count()

        _logger.info("Orphaned consumer profiles to process: %s" % profiles_total)

        for skip_idx in range(0, profiles_total, profiles_batch_size):
            skip_stage = {"$skip": skip_idx}
            limit_stage = {"$limit": profiles_batch_size}
            group_stage = {"$group": {"_id": None, "profile_hash": {"$push": "$_id"}}}
            agg_result = orphaned_profiles_collection.aggregate([skip_stage,
                                                                 limit_stage,
                                                                 group_stage])
            profiles_to_remove = agg_result.next()['profile_hash']
            rpa_collection.remove({'profile_hash': {'$in': profiles_to_remove}})

            # Statistics
            if profiles_total <= profiles_batch_size + skip_idx:
                profiles_removed = profiles_total
            else:
                profiles_removed = profiles_batch_size + skip_idx
            _logger.info("Orphaned consumer profiles processed: %s" % profiles_removed)


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

    # Fill out the mapping of consumer_ids to profiles, and store the list of all_profiles_hashes
    all_profiles_hashes = _add_profiles_to_consumer_map_and_get_hashes(consumer_ids, consumer_map)

    # Now add in repo_ids that the consumers are bound to
    _add_repo_ids_to_consumer_map(consumer_ids, consumer_map)
    # We don't need the list of consumer_ids anymore, so let's free a little RAM
    del consumer_ids

    # Now lets get all RepoProfileApplicability objects that have the profile hashes for our
    # consumers
    applicability_map = _get_applicability_map(all_profiles_hashes, content_types)
    # We don't need the profile_hashes anymore, so let's free some RAM
    del all_profiles_hashes

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
    :param applicability_map: The mapping of (all_profiles_hash, repo_id) to applicability_data and
                              consumer_ids the data applies to. This method appends
                              consumer_ids to the appropriate lists of consumer_ids
    :type  applicability_map: dict
    """
    for consumer_id, repo_profile_data in consumer_map.items():
        profiles = repo_profile_data['profiles']
        profile_hashes = [p['profile_hash'] for p in profiles]
        all_profiles_hash = _calculate_all_profiles_hash(profile_hashes)
        for repo_id in repo_profile_data['repo_ids']:
            repo_profile = (all_profiles_hash, repo_id)
            # Only add the consumer to the applicability map if there is applicability_data
            # for this combination of repository and profile
            if repo_profile in applicability_map:
                applicability_map[repo_profile]['consumers'].append(consumer_id)


def _add_profiles_to_consumer_map_and_get_hashes(consumer_ids, consumer_map):
    """
    Query for all the profiles associated with the given list of consumer_ids, add those
    profiles to the consumer_map, and then return a list of all all_profiles_hashes.

    :param consumer_ids: A list of consumer_ids that we want to map the profiles to
    :type  consumer_ids: list
    :param consumer_map: A dictionary mapping consumer_ids to a dictionary with key 'profiles',
                         which indexes a list that this method will append the found profiles
                         to.
    :type  consumer_map: dict
    :return:             A list of the all_profiles_hashes that were associated with the given
                         consumers
    :rtype:              list
    """
    profiles = UnitProfile.get_collection().find(
        {'consumer_id': {'$in': consumer_ids}, 'profile': {'$ne': []}},
        projection=['consumer_id', 'profile_hash'])
    all_profiles_hashes = set()
    for p in profiles:
        consumer_map[p['consumer_id']]['profiles'].append(p)

    for con_data in consumer_map.values():
        con_profiles = con_data['profiles']
        con_profile_hashes = [p['profile_hash'] for p in con_profiles]
        all_profiles_hash = _calculate_all_profiles_hash(con_profile_hashes)
        all_profiles_hashes.add(all_profiles_hash)
    # Let's return a list of all the unique profile_hashes for the query we will do a
    # bit later for applicability data
    return list(all_profiles_hashes)


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
        projection=['consumer_id', 'repo_id'])
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


def _get_applicability_map(all_profiles_hashes, content_types):
    """
    Build an "applicability_map", which is a dictionary that maps tuples of
    (all_profiles_hash, repo_id) to a dictionary of applicability data and consumer_ids. The
    consumer_ids are just initialized to an empty list, so that a later method can add
    consumers to it. For example, it might look like:

    {('all_profiles_hash_1', 'repo_1'): {'applicability': {<applicability_data>}, 'consumers': []}}

    :param all_profiles_hash: A list of all_profiles_hashes that the applicabilities should be
                              queried with. The applicability map is initialized with all
                              applicability data for all the given all_profiles_hashes.
    :type  all_profiles_hash: list
    :param content_types:  If not None, content_types is a list of content_types to
                           be included in the applicability data within the
                           applicability_map
    :type  content_types:  list or None
    :return:               The applicability map
    :rtype:                dict
    """

    applicabilities = RepoProfileApplicability.get_collection().find(
        {'all_profiles_hash': {'$in': all_profiles_hashes}},
        projection=['all_profiles_hash', 'repo_id', 'applicability'])
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
        return_value[(a['all_profiles_hash'], a['repo_id'])] = {'applicability': a['applicability'],
                                                                'consumers': []}
    return return_value


def _get_consumer_applicability_map(applicability_map):
    """
    Massage the applicability_map into a form that will help us to collate applicability
    groups that contain the same data together.

    :param applicability_map: The mapping of (all_profile_hash, repo_id) to applicability_data and
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
                        set(consumer_applicability_map[consumers][content_type]) |
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


def _calculate_all_profiles_hash(profile_hashes):
    """
    Calculate a hash of consumer profiles' hashes.

    To be able to easily match set of all related profiles.

    :param profile_hashes: list of hashes to calculate a hash from
    :type  profile_hashes: list

    :return: all_profiles_hash
    :rtype: str
    """
    if len(profile_hashes) == 1:
        # for backward compatibility when only one consumer profile exists
        return profile_hashes[0]
    serialized_profile_hashes = json.dumps(sorted(profile_hashes))
    hasher = hashlib.sha256(serialized_profile_hashes)
    return hasher.hexdigest()
