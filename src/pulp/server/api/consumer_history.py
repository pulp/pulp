# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

'''
Consumer history related API methods.
'''

# Python
import datetime
import logging

# 3rd Party
import pymongo

# Pulp
from pulp.common import dateutils
from pulp.server import async
from pulp.server import config
from pulp.server.api.base import BaseApi
from pulp.server.auth.principal import get_principal
from pulp.server.db.model import Consumer, ConsumerHistoryEvent
from pulp.server.exceptions import PulpException
from pulp.server.tasking.scheduler import IntervalScheduler
from pulp.server.tasking.task import Task


# -- constants ----------------------------------------

LOG = logging.getLogger(__name__)

# Event Types
TYPE_CONSUMER_REGISTERED = 'consumer_registered'
TYPE_CONSUMER_UNREGISTERED = 'consumer_unregistered'
TYPE_REPO_BOUND = 'repo_bound'
TYPE_REPO_UNBOUND = 'repo_unbound'
TYPE_PACKAGE_INSTALLED = 'package_installed'
TYPE_PACKAGE_UNINSTALLED = 'package_uninstalled'
TYPE_ERRATA_INSTALLED = 'errata_installed'
TYPE_PROFILE_CHANGED = 'profile_changed'

TYPES = (TYPE_CONSUMER_REGISTERED, TYPE_CONSUMER_UNREGISTERED, TYPE_REPO_BOUND,
         TYPE_REPO_UNBOUND, TYPE_PACKAGE_INSTALLED, TYPE_PACKAGE_UNINSTALLED,
         TYPE_ERRATA_INSTALLED, TYPE_PROFILE_CHANGED)

# Maps user entered query sort parameters to the pymongo representation
SORT_ASCENDING = 'ascending'
SORT_DESCENDING = 'descending'
SORT_DIRECTION = {
    SORT_ASCENDING : pymongo.ASCENDING,
    SORT_DESCENDING : pymongo.DESCENDING,
}


class ConsumerHistoryApi(BaseApi):

    # -- setup ----------------------------------------

    def _getcollection(self):
        return ConsumerHistoryEvent.get_collection()

    def _get_consumer_collection(self):
        '''
        The circular dependency of requiring the consumer API causes issues, so
        when looking up a consumer as a validation check we go directly to the consumer
        collection. This method returns a hook to that collection.

        @return: pymongo database connection to the consumer connection
        @rtype:  ?
        '''
        return Consumer.get_collection()

    # -- public api ----------------------------------------

    def query(self, consumer_id=None, event_type=None, limit=None, sort='descending',
              start_date=None, end_date=None):
        '''
        Queries the consumer history storage.

        @param consumer_id: if specified, events will only be returned for the the
                            consumer referenced; an error is raised if there is no
                            consumer for the given ID
        @type  consumer_id: string or number

        @param event_type: if specified, only events of the given type are returned;
                           an error is raised if the event type mentioned is not listed
                           in the results of the L{event_types} call
        @type  event_type: string (enumeration found in TYPES)

        @param limit: if specified, the query will only return up to this amount of
                      entries; default is to not limit the entries returned
        @type  limit: number greater than zero

        @param sort: indicates the sort direction of the results; results are sorted
                     by timestamp
        @type  sort: string; valid values are 'ascending' and 'descending'

        @param start_date: if specified, no events prior to this date will be returned
        @type  start_date: L{datetime.datetime}

        @param end_date: if specified, no events after this date will be returned
        @type  end_date: L{datetime.datetime}

        @return: list of consumer history entries that match the given parameters;
                 empty list (not None) if no matching entries are found
        @rtype:  list of L{pulp.server.db.model.ConsumerHistoryEvent} instances

        @raise PulpException: if any of the input values are invalid
        '''

        # Verify the consumer ID represents a valid consumer
        if consumer_id:
            consumer_db = self._get_consumer_collection()
            if len(list(consumer_db.find({'id' : consumer_id}))) == 0:
                raise PulpException('Invalid consumer ID [%s]' % consumer_id)

        # Verify the event type is valid
        if event_type and event_type not in TYPES:
            raise PulpException('Invalid event type [%s]' % event_type)

        # Verify the limit makes sense
        if limit is not None and limit < 1:
            raise PulpException('Invalid limit [%s], limit must be greater than zero' % limit)

        # Verify the sort direction was valid
        if not sort in SORT_DIRECTION:
            valid_sorts = ', '.join(SORT_DIRECTION)
            raise PulpException('Invalid sort direction [%s], valid values [%s]' % (sort, valid_sorts))

        # Assemble the mongo search parameters
        search_params = {}
        if consumer_id:
            search_params['consumer_id'] = consumer_id
        if event_type:
            search_params['type_name'] = event_type

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
            cursor = self.collection.find()
        else:
            cursor = self.collection.find(search_params)

        # Sort by most recent entry first
        cursor.sort('timestamp', direction=SORT_DIRECTION[sort])

        # If a limit was specified, add it to the cursor
        if limit:
            cursor.limit(limit)

        # Finally convert to a list before returning
        return list(cursor)

    def event_types(self):
        return TYPES

    # -- internal ----------------------------------------

    def _originator(self):
        '''
        Returns the value to use as the originator of the consumer event (either the
        consumer itself or an admin user).

        @return: login of the originator value to use in the event
        @rtype:  string
        '''
        return get_principal()['login']

    def consumer_registered(self, consumer_id):
        '''
        Creates a new event to represent a consumer being created.

        @param consumer_id: identifies the newly created consumer
        @type  consumer_id: string or number
        '''
        event = ConsumerHistoryEvent(consumer_id, self._originator(),
            TYPE_CONSUMER_REGISTERED, None)
        self.collection.insert(event, safe=True)

    def consumer_unregistered(self, consumer_id):
        '''
        Creates a new event to represent a consumer being deleted.

        @param consumer_id: identifies the deleted consumer
        @type  consumer_id: string or number
        '''
        event = ConsumerHistoryEvent(consumer_id, self._originator(),
            TYPE_CONSUMER_UNREGISTERED, None)
        self.collection.insert(event, safe=True)

    def repo_bound(self, consumer_id, repo_id):
        '''
        Creates a new event to represent a consumer binding to a repo.

        @param consumer_id: identifies the consumer being modified
        @type  consumer_id: string or number

        @param repo_id: identifies the repo being bound to the consumer
        @type  repo_id: string or number
        '''
        details = {'repo_id' : repo_id}
        event = ConsumerHistoryEvent(consumer_id, self._originator(), TYPE_REPO_BOUND, details)
        self.collection.insert(event, safe=True)

    def repo_unbound(self, consumer_id, repo_id):
        '''
        Creates a new event to represent removing a binding from a repo.

        @param consumer_id: identifies the consumer being modified
        @type  consumer_id: string or number

        @param repo_id: identifies the repo being unbound from the consumer
        @type  repo_id: string or number
        '''
        details = {'repo_id' : repo_id}
        event = ConsumerHistoryEvent(consumer_id, self._originator(), TYPE_REPO_UNBOUND, details)
        self.collection.insert(event, safe=True)

    def packages_installed(self, consumer_id, package_nveras, errata_titles=None):
        '''
        Creates a new event to represent packages that were installed on a consumer.

        @param consumer_id: identifies the consumer being modified
        @type  consumer_id: string or number

        @param package_nveras: identifies the packages that were installed on the consumer
        @type  package_nveras: list or string; a single string will automatically be wrapped
                               in a list

        @param errata_titles: if the package installs are the result of applying errata,
                              this is the list of errata titles that were requested
        @type  errata_titles: list of strings
        '''
        if type(package_nveras) != list:
            package_nveras = [package_nveras]

        details = {'package_nveras' : package_nveras,
                   'errata_titles'  : errata_titles, }

        # If any errata were installed, flag the consumer event as an errata install;
        # otherwise flag it as a plain package installation
        if errata_titles:
            event_type = TYPE_ERRATA_INSTALLED
        else:
            event_type = TYPE_PACKAGE_INSTALLED

        event = ConsumerHistoryEvent(consumer_id, self._originator(), event_type, details)
        self.collection.insert(event, check_keys=False, safe=True)

    def packages_removed(self, consumer_id, package_nveras):
        '''
        Creates a new event to represent packages that were removed from a consumer.

        @param consumer_id: identifies the consumer being modified
        @type  consumer_id: string or number

        @param package_nveras: identifies the packages that were removed from the consumer
        @type  package_nveras: list or string; a single string will automatically be wrapped
                               in a list
        '''
        if type(package_nveras) != list:
            package_nveras = [package_nveras]

        details = {'package_nveras' : package_nveras}
        event = ConsumerHistoryEvent(consumer_id, self._originator(), TYPE_PACKAGE_UNINSTALLED, details)
        self.collection.insert(event, check_keys=False, safe=True)

    def profile_updated(self, consumer_id, package_profile):
        '''
        Creates a new event to represent a consumer's package profile has been updated. The
        entire profile will be snapshotted in this event, whereas the consumer will only
        hold on to its current profile.

        @param consumer_id: identifies the consumer being modified
        @type  consumer_id: string or number

        @param package_profile: consumer's full package profile that was sent to the server
        @type  package_profile: dict
        '''
        details = {'package_profile' : package_profile}
        event = ConsumerHistoryEvent(consumer_id, self._originator(), TYPE_PROFILE_CHANGED, details)
        self.collection.insert(event, check_keys=False, safe=True)

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

# recurring culling of consumer history ---------------------------------------

def cull_history():
    api = ConsumerHistoryApi()
    lifetime = api._get_lifetime()
    if lifetime != -1:
        api.cull_history(lifetime)


def init_culling_task():
    interval = datetime.timedelta(days=1)
    tz = dateutils.local_tz()
    now = datetime.datetime.now(tz)
    if now.hour > 1:
        now += interval
    start_time = datetime.datetime(now.year, now.month, now.day, 1, tzinfo=tz)
    scheduler = IntervalScheduler(interval, start_time)
    task = Task(cull_history, scheduler=scheduler)
    async.enqueue(task)
