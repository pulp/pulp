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
Contains profile management classes
"""

from pymongo.errors import DuplicateKeyError
from pulp.server.db.model.consumer import UnitProfile
from pulp.server.managers import factory
from logging import getLogger


_LOG = getLogger(__name__)


class ProfileManager(object):
    """
    Manage consumer installed content unit profiles.
    """

    def create(self, consumer_id, content_type, profile):
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
        return self.update(consumer_id, content_type, profile)

    def update(self, consumer_id, content_type, profile):
        """
        Update a unit profile.
        Created if not already exists.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param content_type: The profile (content) type ID.
        @type content_type: str
        @param profile: The unit profile
        @type profile: object
        """
        manager = factory.consumer_manager()
        manager.get_consumer(consumer_id)
        p = self.get_profile(consumer_id, content_type)
        if p is None:
            p = UnitProfile(consumer_id, content_type, profile)
        else:
            p['profile'] = profile
        collection = UnitProfile.get_collection()
        collection.save(p, safe=True)
        return p

    def delete(self, consumer_id, content_type):
        """
        Delete a profile by consumer and content type.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param content_type: The profile (content) type ID.
        @type content_type: str
        """
        profile = self.get_profile(consumer_id, content_type)
        if profile is not None:
            collection = UnitProfile.get_collection()
            collection.remove(profile, safe=True)

    def consumer_deleted(self, id):
        """
        Notification that a consumer has been deleted.
        Associated profiles are removed.
        @param id: uniquely identifies the consumer.
        @type id: str
        """
        collection = UnitProfile.get_collection()
        for p in self.get_profiles(id):
            collection.remove(p, sefe=True)

    def get_profile(self, consumer_id, content_type):
        """
        Get a profile by consumer ID and content type ID.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param content_type: The profile (content) type ID.
        @type content_type: str
        @return: The requested profile.
        @rtype: object
        """
        collection = UnitProfile.get_collection()
        query = dict(consumer_id=consumer_id, content_type=content_type)
        return collection.find_one(query)

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

    def find_profiles(self, consumer_ids):
        """
        Get all profiles associated with lost of consumers.
        @param consumer_ids: A list of consumer IDs.
        @type consumer_ids: list
        @return: A dict of:
            {consumer_id:{content_type:<profile>}}
        @rtype: list
        """
        profiles = dict([(c, {}) for c in consumer_ids])
        collection = UnitProfile.get_collection()
        for p in collection.find({'id':{'$in':profiles.keys()}}):
            key = p['consumer_id']
            typeid = p['content_type']
            profile = p['profile']
            entry = profiles[key]
            entry[typeid] = profile
        return profiles