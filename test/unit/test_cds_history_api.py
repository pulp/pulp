#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

# Python
import datetime
import os
import sys
import time
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"

sys.path.insert(0, srcdir)
commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'

sys.path.insert(0, commondir)

from pulp.server.api.cds_history import CDSHistoryApi
import pulp.server.auth.auth as auth
from pulp.server.db.model import CDSHistoryEventType, User
from pulp.server.pexceptions import PulpException
import testutil

class TestCDSHistoryApi(unittest.TestCase):

    def setUp(self):
        self.config = testutil.load_test_config()
        self.cds_history_api = CDSHistoryApi()

        self.user = User('cds_admin', '12345', 'password', 'CDS User')
        auth.set_principal(self.user)

    def tearDown(self):
        self.cds_history_api.clean()
        testutil.common_cleanup()

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