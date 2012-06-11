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

# 3rd Party
import pymongo

# Pulp
from pulp.common import dateutils
from pulp.server.api.base import BaseApi
from pulp.server.auth.principal import get_principal
from pulp.server.db.model import CDSHistoryEventType, CDSHistoryEvent
from pulp.server.exceptions import PulpException

# -- globals ---------------------------------------------------------------------

# Maps user entered query sort parameters to the pymongo representation
SORT_ASCENDING = 'ascending'
SORT_DESCENDING = 'descending'
SORT_DIRECTION = {
    SORT_ASCENDING : pymongo.ASCENDING,
    SORT_DESCENDING : pymongo.DESCENDING,
}

# -- api ---------------------------------------------------------------------

class CdsHistoryApi(BaseApi):

    def _getcollection(self):
        return CDSHistoryEvent.get_collection()

# -- public api ---------------------------------------------------------------------

    def query(self, cds_hostname=None, event_type=None, limit=None, sort='descending',
              start_date=None, end_date=None):
        '''
        Queries the CDS history storage.

        @param cds_hostname: if specified, events will only be returned for the
                             CDS referenced
        @type  cds_hostname: string

        @param event_type: if specified, only events of the given type are returned;
                           an error is raised if the event type mentioned is not valid
        @type  event_type: string (enumeration found in L{pulp.server.db.model.CDSHistoryEvent})

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

        @return: list of CDS history entries that match the given parameters;
                 empty list (not None) if no matching entries are found
        @rtype:  list of L{pulp.server.db.model.CDSHistoryEvent} instances

        @raise PulpException: if any of the input values are invalid
        '''

        # Verify the event type is valid
        if event_type is not None and event_type not in CDSHistoryEventType.TYPES:
            valid_types = ', '.join(CDSHistoryEventType.TYPES)
            raise PulpException('Invalid event type [%s], valid types are [%s]' % (event_type, valid_types))

        # Verify the limit makes sense
        if limit is not None and limit < 1:
            raise PulpException('Invalid limit [%s], limit must be greater than zero' % limit)

        # Verify the sort direction was valid
        if not sort in SORT_DIRECTION:
            valid_sorts = ', '.join(SORT_DIRECTION)
            raise PulpException('Invalid sort direction [%s], valid values [%s]' % (sort, valid_sorts))

        # Assemble the mongo search parameters
        search_params = {}
        if cds_hostname:
            search_params['cds_hostname'] = cds_hostname
        if event_type:
            search_params['type_name'] = event_type

        # Determine the correct mongo cursor to retrieve
        if len(search_params) == 0:
            cursor = self.collection.find()
        else:
            cursor = self.collection.find(search_params)

        # Sort by most recent entry first
        cursor.sort([('id', pymongo.DESCENDING)])

        def _within_start_end(h):
            timestamp = dateutils.parse_iso8601_datetime(h['timestamp'])
            if start_date is not None and timestamp < start_date:
                return False
            if end_date is not None and timestamp > end_date:
                return False
            return True

        history = [h for h in cursor if _within_start_end(h)]

        def _cmp_history(h1, h2):
            t1 = dateutils.parse_iso8601_datetime(h1['timestamp'])
            t2 = dateutils.parse_iso8601_datetime(h2['timestamp'])
            return cmp(t1, t2)

        reverse = sort == SORT_DESCENDING
        history = sorted(history, cmp=_cmp_history, reverse=reverse)

        # If a limit was specified, add it to the cursor
        if limit:
            history = history[:limit]

        return history

# -- internal only api ---------------------------------------------------------------------

    def _originator(self):
        '''
        Returns the value to use as the originator of the event (either the "system" user
        or an admin user).

        @return: login of the originator value to use in the event
        @rtype:  string
        '''
        return get_principal()['login']

    def cds_registered(self, cds_hostname):
        '''
        Creates a new event to represent a CDS being registered with the server.

        @param cds_hostname: identifies the CDS; may not be None
        @type  cds_hostname: string
        '''
        if cds_hostname is None:
            raise PulpException('CDS hostname must be specified')

        event = CDSHistoryEvent(cds_hostname, self._originator(), CDSHistoryEventType.REGISTERED)
        self.collection.insert(event, safe=True)

    def cds_unregistered(self, cds_hostname):
        '''
        Creates a new event to represent a CDS being unregistered from the server.

        @param cds_hostname: identifies the CDS; may not be None
        @type  cds_hostname: string
        '''
        if cds_hostname is None:
            raise PulpException('CDS hostname must be specified')

        event = CDSHistoryEvent(cds_hostname, self._originator(), CDSHistoryEventType.UNREGISTERED)
        self.collection.insert(event, safe=True)

    def repo_associated(self, cds_hostname, repo_id):
        '''
        Creates a new event to represent a repo being associated with a CDS.

        @param cds_hostname: identifies the CDS; may not be None
        @type  cds_hostname: string

        @param repo_id: identifies the repo that was associated to the CDS; may not be None
        @type  repo_id: string
        '''
        if cds_hostname is None:
            raise PulpException('CDS hostname must be specified')

        if repo_id is None:
            raise PulpException('Repo ID must be specified')

        details = {'repo_id' : repo_id}
        event = CDSHistoryEvent(cds_hostname, self._originator(), CDSHistoryEventType.REPO_ASSOCIATED, details)
        self.collection.insert(event, safe=True)

    def repo_unassociated(self, cds_hostname, repo_id):
        '''
        Creates a new event to represent a repo's association with a CDS being removed.

        @param cds_hostname: identifies the CDS; may not be None
        @type  cds_hostname: string

        @param repo_id: identifies the repo whose association was removed; may not be None
        @type  repo_id: string
        '''
        if cds_hostname is None:
            raise PulpException('CDS hostname must be specified')

        if repo_id is None:
            raise PulpException('Repo ID must be specified')

        details = {'repo_id' : repo_id}
        event = CDSHistoryEvent(cds_hostname, self._originator(), CDSHistoryEventType.REPO_UNASSOCIATED, details)
        self.collection.insert(event, safe=True)

    def sync_started(self, cds_hostname):
        '''
        Creates a new event to represent the beginning of a CDS sync.

        @param cds_hostname: identifies the CDS; may not be None
        @type  cds_hostname: string
        '''
        if cds_hostname is None:
            raise PulpException('CDS hostname must be specified')

        event = CDSHistoryEvent(cds_hostname, self._originator(), CDSHistoryEventType.SYNC_STARTED)
        self.collection.insert(event, safe=True)

    def sync_finished(self, cds_hostname, error=None):
        '''
        Creates a new event to represent the completion of a CDS sync, including error
        information if one occurred.

        @param cds_hostname: identifies the CDS; may not be None
        @type  cds_hostname: string

        @param error: if specified, stores information on an error that occurred during the sync
        @type  error: string; may be None
        '''
        if cds_hostname is None:
            raise PulpException('CDS hostname must be specified')

        details = {'error' : error}
        event = CDSHistoryEvent(cds_hostname, self._originator(), CDSHistoryEventType.SYNC_FINISHED, details)
        self.collection.insert(event, safe=True)

