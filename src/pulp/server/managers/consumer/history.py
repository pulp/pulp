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
Contains manager class and exceptions for operations for recording and retrieving
consumer history events.
"""

import logging
import datetime
import pymongo

from pulp.common import dateutils
from pulp.server import config
from pulp.server.auth.principal import get_principal

from pulp.server.db.model.gc_consumer import Consumer, ConsumerHistoryEvent
from pulp.server.exceptions import InvalidValue, MissingResource

# -- constants ----------------------------------------------------------------

# Event Types
TYPE_CONSUMER_REGISTERED = 'consumer_registered'
TYPE_CONSUMER_UNREGISTERED = 'consumer_unregistered'
TYPE_REPO_BOUND = 'repo_bound'
TYPE_REPO_UNBOUND = 'repo_unbound'
TYPE_CONTENT_UNIT_INSTALLED = 'content_unit_installed'
TYPE_CONTENT_UNIT_UNINSTALLED = 'content_unit_uninstalled'
TYPE_UNIT_PROFILE_CHANGED = 'unit_profile_changed'
TYPE_ADDED_TO_GROUP = 'added_to_group'
TYPE_REMOVED_FROM_GROUP = 'removed_from_group'

TYPES = (TYPE_CONSUMER_REGISTERED, TYPE_CONSUMER_UNREGISTERED, TYPE_REPO_BOUND,
         TYPE_REPO_UNBOUND, TYPE_CONTENT_UNIT_INSTALLED, TYPE_CONTENT_UNIT_UNINSTALLED,
         TYPE_UNIT_PROFILE_CHANGED, TYPE_ADDED_TO_GROUP, TYPE_REMOVED_FROM_GROUP)

# Maps user entered query sort parameters to the pymongo representation
SORT_ASCENDING = 'ascending'
SORT_DESCENDING = 'descending'
SORT_DIRECTION = {
    SORT_ASCENDING : pymongo.ASCENDING,
    SORT_DESCENDING : pymongo.DESCENDING,
}


_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class ConsumerHistoryManager(object):
    """
    Performs consumer related CRUD operations
    """

    # -- internal ----------------------------------------

    def _originator(self):
        '''
        Returns the value to use as the originator of the consumer event (either the
        consumer itself or an admin user).

        @return: login of the originator value to use in the event
        @rtype:  string
        '''
        return get_principal()['login']


    def record_event(self, consumer_id, event_type, event_details=None):
        """
        @ivar consumer_id: identifies the consumer
        @type id: str

        @param type: event type
        @type type: str

        @param details: event details
        @type details: dict

        @raises MissingResource: if the given consumer does not exist
        @raises InvalidValue: if any of the fields is unacceptable
        """
        # Check that consumer exists for all except registration event
        existing_consumer = Consumer.get_collection().find_one({'id' : consumer_id})
        if not existing_consumer and event_type != TYPE_CONSUMER_UNREGISTERED:
            raise MissingResource(consumer=consumer_id)

        invalid_values = []
        if event_type not in TYPES:
            invalid_values.append('event_type')
            
        if event_details is not None and not isinstance(event_details, dict):
            invalid_values.append('event_details')
            
        if invalid_values:
            raise InvalidValue(invalid_values)
            
        event = ConsumerHistoryEvent(consumer_id, self._originator(), event_type, event_details)
        ConsumerHistoryEvent.get_collection().save(event, safe=True)


    def query(self, consumer_id, event_type=None, limit=None, sort='descending',
              start_date=None, end_date=None):
        '''
        Queries the consumer history storage.

        @param consumer_id: if specified, events will only be returned for the the
                            consumer referenced
        @type  consumer_id: string or number

        @param event_type: if specified, only events of the given type are returned
        @type  event_type: string (enumeration found in TYPES)

        @param limit: if specified, the query will only return up to this amount of
                      entries; default is to not limit the entries returned
        @type  limit: number greater than zero

        @param sort: indicates the sort direction of the results; results are sorted
                     by timestamp
        @type  sort: string; valid values are 'ascending' and 'descending'

        @param start_date: if specified, no events prior to this date will be returned
        @type  start_date: datetime.datetime

        @param end_date: if specified, no events after this date will be returned
        @type  end_date: datetime.datetime

        @return: list of consumer history entries that match the given parameters;
                 empty list (not None) if no matching entries are found
        @rtype:  list of ConsumerHistoryEvent instances

        @raises MissingResource: if the given consumer does not exist
        @raises InvalidValue: if any of the fields is unacceptable
        '''
        # Verify the consumer ID represents a valid consumer
        existing_consumer = Consumer.get_collection().find_one({'id' : consumer_id})
        if not existing_consumer:
            raise MissingResource(consumer=consumer_id)

        invalid_values = []
        if event_type is not None and event_type not in TYPES:
            invalid_values.append('event_type')

        # Verify the limit makes sense
        if limit is not None and limit < 1:
            invalid_values.append('limit')

        # Verify the sort direction was valid
        if not sort in SORT_DIRECTION:
            invalid_values.append('sort')
            
        if invalid_values:
            raise InvalidValue(invalid_values)

        # Assemble the mongo search parameters
        search_params = {}
        if consumer_id:
            search_params['consumer_id'] = consumer_id
        if event_type:
            search_params['type'] = event_type

        # Add in date range limits if specified
        date_range = {}
        if start_date:
            date_range['$gte'] = dateutils.format_iso8601_datetime(start_date)
        if end_date:
            date_range['$lte'] = dateutils.format_iso8601_datetime(end_date)

        if len(date_range) > 0:
            search_params['timestamp'] = date_range

        # Determine the correct mongo cursor to retrieve
        if len(search_params) == 0:
            cursor = ConsumerHistoryEvent.get_collection().find()
        else:
            cursor = ConsumerHistoryEvent.get_collection().find(search_params)

        # Sort by most recent entry first
        cursor.sort('timestamp', direction=SORT_DIRECTION[sort])

        # If a limit was specified, add it to the cursor
        if limit:
            cursor.limit(limit)

        # Finally convert to a list before returning
        return list(cursor)

    def event_types(self):
        return TYPES

    def cull_history(self, lifetime):
        '''
        Deletes all consumer history entries that are older than the given lifetime.

        @param lifetime: length in days; history entries older than this many days old
                         are deleted in this call
        @type  lifetime: L{datetime.timedelta}
        '''
        now = datetime.datetime.now(dateutils.local_tz())
        limit = dateutils.format_iso8601_datetime(now - lifetime)
        spec = {'timestamp': {'$lt': limit}}
        self.collection.remove(spec, safe=False)

    def _get_lifetime(self):
        '''
        Returns the configured maximum lifetime for consumer history entries.

        @return: time in days
        @rtype:  L{datetime.timedelta}
        '''
        days = config.config.getint('consumer_history', 'lifetime')
        return datetime.timedelta(days=days)


# -- functions ----------------------------------------------------------------
