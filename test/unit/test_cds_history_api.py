#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.common import dateutils
from pulp.server.api.cds_history import CdsHistoryApi
from pulp.server.auth import principal
from pulp.server.db.model import CDSHistoryEventType, CDSHistoryEvent, User
from pulp.server.exceptions import PulpException

class TestCDSHistoryApi(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.user = User('cds_admin', '12345', 'password', 'CDS User')
        principal.set_principal(self.user)

    def test_cds_registered(self):
        '''
        Tests a valid logging of a CDS registered event.
        '''

        # Test
        self.cds_history_api.cds_registered('cds.example.com')

        # Verify
        events = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(events))
        self.assertEqual(CDSHistoryEventType.REGISTERED, events[0]['type_name'])
        self.assertEqual('cds.example.com', events[0]['cds_hostname'])
        self.assertEqual(self.user.login, events[0]['originator'])
        self.assertEqual(None, events[0]['details'])
        self.assertTrue(events[0]['timestamp'] is not None)

    def test_cds_registered_missing_cds(self):
        '''
        Tests logging a CDS registered event with a missing CDS hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.cds_registered, None)

    def test_cds_unregistered(self):
        '''
        Tests a valid logging of a CDS unregistered event.
        '''

        # Test
        self.cds_history_api.cds_unregistered('cds.example.com')

        # Verify
        events = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(events))
        self.assertEqual(CDSHistoryEventType.UNREGISTERED, events[0]['type_name'])
        self.assertEqual('cds.example.com', events[0]['cds_hostname'])
        self.assertEqual(self.user.login, events[0]['originator'])
        self.assertEqual(None, events[0]['details'])
        self.assertTrue(events[0]['timestamp'] is not None)

    def test_cds_unregistered_missing_cds(self):
        '''
        Tests logging a CDS unregistered event with a missing CDS hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.cds_unregistered, None)

    def test_repo_associated(self):
        '''
        Tests a valid logging of a repo associated event.
        '''

        # Test
        self.cds_history_api.repo_associated('cds.example.com', 'repo1')

        # Verify
        events = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(events))
        self.assertEqual(CDSHistoryEventType.REPO_ASSOCIATED, events[0]['type_name'])
        self.assertEqual('cds.example.com', events[0]['cds_hostname'])
        self.assertEqual(self.user.login, events[0]['originator'])
        self.assertEqual('repo1', events[0]['details']['repo_id'])
        self.assertTrue(events[0]['timestamp'] is not None)

    def test_repo_associated_missing_cds(self):
        '''
        Tests logging a repo associated event with a missing CDS hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.repo_associated, None, 'repo1')

    def test_repo_associated_missing_repo(self):
        '''
        Tests logging a repo associated event with a missing repo ID.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.repo_associated, 'cds.example.com', None)

    def test_repo_unassociated(self):
        '''
        Tests a valid logging of a repo unassociated event.
        '''

        # Test
        self.cds_history_api.repo_unassociated('cds.example.com', 'repo1')

        # Verify
        events = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(events))
        self.assertEqual(CDSHistoryEventType.REPO_UNASSOCIATED, events[0]['type_name'])
        self.assertEqual('cds.example.com', events[0]['cds_hostname'])
        self.assertEqual(self.user.login, events[0]['originator'])
        self.assertEqual('repo1', events[0]['details']['repo_id'])
        self.assertTrue(events[0]['timestamp'] is not None)

    def test_repo_unassociated_missing_cds(self):
        '''
        Tests logging a repo unassociated event with a missing CDS hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.repo_unassociated, None, 'repo1')

    def test_repo_unassociated_missing_repo(self):
        '''
        Tests logging a repo unassociated event with a missing repo ID.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.repo_unassociated, 'cds.example.com', None)

    def test_sync_started(self):
        '''
        Tests logging a valid sync started event.
        '''

        # Test
        self.cds_history_api.sync_started('cds.example.com')

        # Verify
        events = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(events))
        self.assertEqual(CDSHistoryEventType.SYNC_STARTED, events[0]['type_name'])
        self.assertEqual('cds.example.com', events[0]['cds_hostname'])
        self.assertEqual(self.user.login, events[0]['originator'])
        self.assertEqual(None, events[0]['details'])
        self.assertTrue(events[0]['timestamp'] is not None)

    def test_sync_started_missing_cds(self):
        '''
        Tests logging a sync started event with a missing CDS hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.sync_started, None)

    def test_sync_finished_no_error(self):
        '''
        Tests logging a sync finished event with no error in the sync.
        '''

        # Test
        self.cds_history_api.sync_finished('cds.example.com')

        # Verify
        events = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(events))
        self.assertEqual(CDSHistoryEventType.SYNC_FINISHED, events[0]['type_name'])
        self.assertEqual('cds.example.com', events[0]['cds_hostname'])
        self.assertEqual(self.user.login, events[0]['originator'])
        self.assertEqual(None, events[0]['details']['error'])
        self.assertTrue(events[0]['timestamp'] is not None)

    def test_sync_finished_with_error(self):
        '''
        Tests logging a sync finished event, logging an error in the sync.
        '''

        # Test
        self.cds_history_api.sync_finished('cds.example.com', error='1')

        # Verify
        events = self.cds_history_api.query(cds_hostname='cds.example.com')
        self.assertEqual(1, len(events))
        self.assertEqual(CDSHistoryEventType.SYNC_FINISHED, events[0]['type_name'])
        self.assertEqual('cds.example.com', events[0]['cds_hostname'])
        self.assertEqual(self.user.login, events[0]['originator'])
        self.assertEqual('1', events[0]['details']['error'])
        self.assertTrue(events[0]['timestamp'] is not None)

    def test_sync_finished_missing_cds(self):
        '''
        Tests logging a sync finished event with a missing CDS hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.sync_finished, None)

    def test_query_all(self):
        '''
        Tests querying all history entries.
        '''

        # Setup
        self._populate_for_queries()

        # Test
        results = self.cds_history_api.query()

        # Verify
        self.assertEqual(7, len(results));

    def test_query_invalid_type(self):
        '''
        Tests that querying specifying an invalid type throws an exception.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.query, event_type='foo')

    def test_query_negative_limit(self):
        '''
        Tests that querying with a negative limit throws an exception.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.query, limit= -1)

    def test_query_zero_limit(self):
        '''
        Tests that querying with a zero limit throws an exception.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.query, limit=0)

    def test_query_invalid_sort(self):
        '''
        Tests that querying with an invalid sort direction throws an exception.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_history_api.query, sort='foo')

    def test_query_cds_no_entries(self):
        '''
        Tests that querying for a CDS that has no history entries does not throw an exception.
        '''

        # Test
        results = self.cds_history_api.query()

        # Verify
        # The above call should not throw an error
        self.assertEqual(0, len(results))

    def test_query_by_cds(self):
        '''
        Tests scoping a query to a specific CDS.
        '''

        # Setup
        self._populate_for_queries()

        # Test
        results1 = self.cds_history_api.query(cds_hostname='cds-01.example.com')
        results2 = self.cds_history_api.query(cds_hostname='cds-02.example.com')

        # Verify
        self.assertEqual(5, len(results1))
        self.assertEqual(2, len(results2))

        for r in results1:
            self.assertEqual('cds-01.example.com', r['cds_hostname'])

        for r in results2:
            self.assertEqual('cds-02.example.com', r['cds_hostname'])

    def test_query_by_type(self):
        '''
        Tests scoping a query to a specific event type.
        '''

        # Setup
        self._populate_for_queries()

        # Test
        results = self.cds_history_api.query(event_type=CDSHistoryEventType.REGISTERED)

        # Verify
        self.assertEqual(2, len(results))

        for r in results:
            self.assertEqual(CDSHistoryEventType.REGISTERED, r['type_name'])

    def test_query_with_limit(self):
        '''
        Tests limiting the number of returned results to lower than the total amount.
        '''

        # Setup
        self._populate_for_queries()

        # Test
        results = self.cds_history_api.query(limit=3) # populate call adds more than 3

        # Verify
        self.assertEqual(3, len(results))

    def test_query_sort_direction(self):
        '''
        Tests that specifying a result sort properly sorts the results.
        '''

        # Setup
        self.cds_history_api.cds_registered('cds-02.example.com')
        time.sleep(1) # make sure the timestamps will be different
        self.cds_history_api.repo_associated('cds-02.example.com', 'repo3')

        # Test
        ascending = self.cds_history_api.query(sort='ascending')
        descending = self.cds_history_api.query(sort='descending')

        # Verify
        self.assertEqual(2, len(ascending))
        self.assertEqual(2, len(descending))

        self.assertEqual(CDSHistoryEventType.REGISTERED, ascending[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REPO_ASSOCIATED, descending[0]['type_name'])

    def test_query_start_range(self):
        '''
        Tests that specifying a start range properly scopes the results.
        '''

        # Setup
        self._populate_for_date_queries()

        # Test
        start_date = datetime.datetime(2000, 5, 1, tzinfo=dateutils.local_tz())
        results = self.cds_history_api.query(start_date=start_date)

        # Verify
        self.assertEqual(2, len(results))
        self.assertEqual(CDSHistoryEventType.UNREGISTERED, results[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REPO_UNASSOCIATED, results[1]['type_name'])

    def test_query_end_range(self):
        '''
        Tests that specifying an end range properly scopes the results.
        '''

        # Setup
        self._populate_for_date_queries()

        # Test
        end_date = datetime.datetime(2000, 5, 1, tzinfo=dateutils.local_tz())
        results = self.cds_history_api.query(end_date=end_date)

        # Verify
        self.assertEqual(2, len(results))
        self.assertEqual(CDSHistoryEventType.REPO_ASSOCIATED, results[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REGISTERED, results[1]['type_name'])

    def test_query_start_and_end_range(self):
        '''
        Tests that specifying both a start and end range properly scopes the results.
        '''

        # Setup
        self._populate_for_date_queries()

        # Test
        start_date = datetime.datetime(2000, 3, 1, tzinfo=dateutils.local_tz())
        end_date = datetime.datetime(2000, 7, 1, tzinfo=dateutils.local_tz())
        results = self.cds_history_api.query(start_date=start_date, end_date=end_date)

        # Verify
        self.assertEqual(2, len(results))
        self.assertEqual(CDSHistoryEventType.REPO_UNASSOCIATED, results[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REPO_ASSOCIATED, results[1]['type_name'])

    # this test has been removed because of a bug in pulp's faulty timezone support
    # bug 716243
    def __test_query_start_end_date_range_edge_cases(self):
        '''
        Tests that both start and end date ranges are inclusive.
        '''

        # Setup
        self._populate_for_date_queries()

        # Test
        start_date = datetime.datetime(2000, 2, 1, tzinfo=dateutils.local_tz())
        end_date = datetime.datetime(2000, 4, 1, tzinfo=dateutils.local_tz())
        results = self.cds_history_api.query(start_date=start_date, end_date=end_date)

        # Verify
        self.assertEqual(2, len(results))
        self.assertEqual(CDSHistoryEventType.REPO_ASSOCIATED, results[0]['type_name'])
        self.assertEqual(CDSHistoryEventType.REGISTERED, results[1]['type_name'])

# -- test utilities -----------------------------------------------------------------------

    def _populate_for_queries(self):
        '''
        Populates the CDS history collection with a series of entries for query
        related tests.
        '''

        # cds-01.example.com
        self.cds_history_api.cds_registered('cds-01.example.com')
        self.cds_history_api.repo_associated('cds-01.example.com', 'repo1')
        self.cds_history_api.repo_associated('cds-01.example.com', 'repo2')
        self.cds_history_api.sync_started('cds-01.example.com')
        self.cds_history_api.sync_finished('cds-01.example.com')

        # cds-02.example.com
        self.cds_history_api.cds_registered('cds-02.example.com')
        self.cds_history_api.repo_associated('cds-02.example.com', 'repo3')

    def _populate_for_date_queries(self):
        '''
        Populates the CDS history collection with entries staggered by a large date range,
        suitable for being able to query within date ranges.

        The events are manually created and stored in the database; using the API calls
        will cause the timestamps to be set to 'now' in all cases.
        '''

        e1 = CDSHistoryEvent('cds1.example.com', 'admin', CDSHistoryEventType.REGISTERED)
        e2 = CDSHistoryEvent('cds2.example.com', 'admin', CDSHistoryEventType.REPO_ASSOCIATED)
        e3 = CDSHistoryEvent('cds3.example.com', 'admin', CDSHistoryEventType.REPO_UNASSOCIATED)
        e4 = CDSHistoryEvent('cds4.example.com', 'admin', CDSHistoryEventType.UNREGISTERED)

        e1.timestamp = dateutils.format_iso8601_datetime(datetime.datetime(2000, 2, 1, tzinfo=dateutils.utc_tz()))
        e2.timestamp = dateutils.format_iso8601_datetime(datetime.datetime(2000, 4, 1, tzinfo=dateutils.utc_tz()))
        e3.timestamp = dateutils.format_iso8601_datetime(datetime.datetime(2000, 6, 1, tzinfo=dateutils.utc_tz()))
        e4.timestamp = dateutils.format_iso8601_datetime(datetime.datetime(2000, 10, 1, tzinfo=dateutils.utc_tz()))

        self.cds_history_api.collection.insert(e1)
        self.cds_history_api.collection.insert(e2)
        self.cds_history_api.collection.insert(e3)
        self.cds_history_api.collection.insert(e4)
