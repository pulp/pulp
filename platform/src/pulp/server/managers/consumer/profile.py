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
Contains bind management classes
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

    def update(self, consumer_id, type_id, profile):
        """
        Update a unit profile.
        Created if not already exists.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param type_id: The profile (content) type ID.
        @type type_id: str
        @param profile: The unit profile
        @type profile: object
        """
        manager = factory.consumer_manager()
        manager.get_consumer(consumer_id)
        p = self.get_profile(consumer_id, type_id)
        if p is None:
            p = UnitProfile(consumer_id, type_id, profile)
        else:
            p.profile = profile
        collection.save(p, safe=True)
        return p

    def delete(self, consumer_id, type_id):
        """
        Clear the unit profile.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param type_id: The profile type ID.
        @type type_id: str
        """
        pass

    def consumer_deleted(self, id):
        """
        Notification that a consumer has been deleted.
        Associated profiles are removed.
        @param id: A consumer ID.
        @type id: str
        """
        pass

    def get_profile(self, id, type_id):
        """
        Find all profiles by Consumer ID.
        @param id: A consumer ID.
        @type id: str
        @param type_id: A type ID.
        @type type_id: str
        @return: The requested profile.
        @rtype: object
        """
        collection = UnitProfile.get_collection()
        query = dict(consumer_id=id, type_id=type_id)
        return collection.find_one(query)