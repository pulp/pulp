"""
Contains profile management classes
"""
from celery import task

from pulp.plugins.loader import api as plugin_api, exceptions as plugin_exceptions
from pulp.plugins.profiler import Profiler
from pulp.server.async.tasks import Task
from pulp.server.db.model.consumer import UnitProfile
from pulp.server.exceptions import MissingResource, MissingValue
from pulp.server.managers import factory


class ProfileManager(object):
    """
    Manage consumer installed content unit profiles.
    """
    @staticmethod
    def create(consumer_id, content_type, profile):
        """
        Create a unit profile.
        Updated if already exists.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param content_type: The profile (content) type ID.
        @type content_type: str
        @param profile: The unit profile
        @type profile: object
        """
        return ProfileManager.update(consumer_id, content_type, profile)

    @staticmethod
    def update(consumer_id, content_type, profile):
        """
        Update a unit profile.
        Created if not already exists.

        :param consumer_id:  uniquely identifies the consumer.
        :type  consumer_id:  str
        :param content_type: The profile (content) type ID.
        :type  content_type: str
        :param profile:      The unit profile
        :type  profile:      object
        """
        consumer = factory.consumer_manager().get_consumer(consumer_id)
        try:
            profiler, config = plugin_api.get_profiler_by_type(content_type)
        except plugin_exceptions.PluginNotFound:
            # Not all profile types have a type specific profiler, so let's use the baseclass
            # Profiler
            profiler, config = (Profiler(), {})
        # Allow the profiler a chance to update the profile before we save it
        if profile is None:
            raise MissingValue('profile')
        profile = profiler.update_profile(consumer, content_type, profile, config)
        try:
            p = ProfileManager.get_profile(consumer_id, content_type)
            p['profile'] = profile
            # We store the profile's hash anytime the profile gets altered
            p['profile_hash'] = UnitProfile.calculate_hash(profile)
        except MissingResource:
            p = UnitProfile(consumer_id, content_type, profile)
        collection = UnitProfile.get_collection()
        collection.save(p)
        history_manager = factory.consumer_history_manager()
        history_manager.record_event(
            consumer_id,
            'unit_profile_changed', {'profile_content_type': content_type})
        return p

    @staticmethod
    def delete(consumer_id, content_type):
        """
        Delete a profile by consumer and content type.

        :param consumer_id:  uniquely identifies the consumer.
        :type  consumer_id:  str
        :param content_type: The profile (content) type ID.
        :type  content_type: str
        """
        profile = ProfileManager.get_profile(consumer_id, content_type)
        collection = UnitProfile.get_collection()
        collection.remove(profile)

    def consumer_deleted(self, id):
        """
        Notification that a consumer has been deleted.
        Associated profiles are removed.
        @param id: uniquely identifies the consumer.
        @type id: str
        """
        collection = UnitProfile.get_collection()
        for p in self.get_profiles(id):
            collection.remove(p)

    @staticmethod
    def get_profile(consumer_id, content_type):
        """
        Get a profile by consumer ID and content type ID.

        :param consumer_id:     uniquely identifies the consumer.
        :type consumer_id:      str
        :param content_type:    The profile (content) type ID.
        :type content_type:     str
        :return:                The requested profile.
        :rtype:                 object
        :raise MissingResource: when profile not found.
        """
        collection = UnitProfile.get_collection()
        profile_id = dict(consumer_id=consumer_id, content_type=content_type)
        profile = collection.find_one(profile_id)
        if profile is None:
            raise MissingResource(profile_id=profile_id)
        else:
            return profile

    def get_profiles(self, consumer_id):
        """
        Get all profiles associated with a consumer.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @return: A list of profiles:
            {consumer_id:<str>, content_type:<str>, profile:<dict>}
        @rtype: list
        """
        collection = UnitProfile.get_collection()
        query = dict(consumer_id=consumer_id)
        cursor = collection.find(query)
        return list(cursor)

    @staticmethod
    def find_by_criteria(criteria):
        """
        Return a list of unit profiles that match the provided criteria.

        @param criteria:    A Criteria object representing a search you want
                            to perform
        @type  criteria:    pulp.server.db.model.criteria.Criteria

        @return:    list of UnitProfile instances
        @rtype:     list
        """
        return UnitProfile.get_collection().query(criteria)


create = task(ProfileManager.create, base=Task)
delete = task(ProfileManager.delete, base=Task, ignore_result=True)
update = task(ProfileManager.update, base=Task)
