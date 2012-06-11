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
Contains consumer query classes
"""

from pulp.server.db.model.gc_consumer import Consumer
from logging import getLogger

# -- constants ----------------------------------------------------------------

_LOG = getLogger(__name__)

# -- manager ------------------------------------------------------------------


class ConsumerQueryManager(object):
    
    """
    Manager used to process queries on consumers. Consumers returned from
    these calls are consumer SON objects from the database.
    """

    def find_all(self):
        """
        Returns all consumers in the database.
        If there are no consumers defined, an empty list is returned.

        @return: list of serialized consumers
        @rtype:  list of dict
        """
        all_consumers = list(Consumer.get_collection().find())
        return all_consumers


    def find_by_id(self, id):
        """
        Find a consumer by ID. 
        
        @param id: The consumer ID.
        @type id: str
        
        @return: The consumer model object. None if no consumer exists with given ID.
        @rtype: L{Consumer}
        
        """
        collection = Consumer.get_collection()
        consumer = collection.find_one({'id':id})
        return consumer
    
    def find_by_id_list(self, consumer_id_list):
        """
        Returns details of all of the given consumers. Any IDs that do not refer to a valid consumer 
        are ignored and will not raise an error.

        @param consumer_id_list: list of consumer IDs to fetch
        @type  consumer_id_list: list of str

        @return: list of serialized consumers
        @rtype:  list of dict
        """
        consumers = Consumer.get_collection().find({'id' : {'$in' : consumer_id_list}})
        return list(consumers)
    
    def find_by_notes(self, notes):
        pass

    def find_by_content_unit(self, unit_id):
        pass

