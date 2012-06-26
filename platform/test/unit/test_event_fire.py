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

import base
import mock

from pulp.server.db.model.event import EventListener
from pulp.server.event import notifiers
from pulp.server.event import data as event_data
from pulp.server.managers import factory as manager_factory


class EventFireManagerTests(base.PulpServerTests):

    def setUp(self):
        super(EventFireManagerTests, self).setUp()

        self.manager = manager_factory.event_fire_manager()
        self.event_manager = manager_factory.event_listener_manager()

    def tearDown(self):
        super(EventFireManagerTests, self).tearDown()

        EventListener.get_collection().remove()
        notifiers.reset()

    # -- plumbing tests -------------------------------------------------------

    def test_do_fire(self):
        # Setup
        notifiers.NOTIFIER_FUNCTIONS.clear()

        notifier_1 = mock.Mock()
        notifier_2 = mock.Mock()
        notifier_3 = mock.Mock()

        notifiers.NOTIFIER_FUNCTIONS['notifier_1'] = notifier_1.fire
        notifiers.NOTIFIER_FUNCTIONS['notifier_2'] = notifier_2.fire
        notifiers.NOTIFIER_FUNCTIONS['notifier_3'] = notifier_3.fire

        self.event_manager.create('notifier_1', {'1' : '1'}, [event_data.TYPE_REPO_SYNC_STARTED])
        self.event_manager.create('notifier_2', {'2' : '2'}, [event_data.TYPE_REPO_SYNC_STARTED, event_data.TYPE_REPO_SYNC_FINISHED])
        self.event_manager.create('notifier_3', {'3' : '3'}, [event_data.TYPE_REPO_SYNC_FINISHED])

        # Test
        event = event_data.Event(event_data.TYPE_REPO_SYNC_STARTED, 'payload')
        self.manager._do_fire(event)

        # Verify
        self.assertEqual(1, notifier_1.fire.call_count)
        self.assertEqual(1, notifier_2.fire.call_count)
        self.assertEqual(0, notifier_3.fire.call_count)

        self.assertEqual({'1' : '1'}, notifier_1.fire.call_args[0][0])
        self.assertEqual(event, notifier_1.fire.call_args[0][1])

        self.assertEqual({'2' : '2'}, notifier_2.fire.call_args[0][0])
        self.assertEqual(event, notifier_2.fire.call_args[0][1])

    def test_do_fire_with_exception(self):
        # Setup
        notifiers.NOTIFIER_FUNCTIONS.clear()

        notifier_1 = mock.Mock()
        notifier_2 = mock.Mock()

        notifiers.NOTIFIER_FUNCTIONS['notifier_1'] = notifier_1.fire
        notifiers.NOTIFIER_FUNCTIONS['notifier_2'] = notifier_2.fire

        notifier_1.fire.side_effect = Exception('Exception from notifier fire')

        self.event_manager.create('notifier_1', {'1' : '1'}, [event_data.TYPE_REPO_SYNC_STARTED])
        self.event_manager.create('notifier_2', {'2' : '2'}, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        event = event_data.Event(event_data.TYPE_REPO_SYNC_STARTED, 'payload')
        self.manager._do_fire(event)

        # Verify

        # The main purpose of the test is that an exception was not raised.
        # We should also double-check that the second notifier was still invoked.

        self.assertEqual(1, notifier_1.fire.call_count)
        self.assertEqual(1, notifier_2.fire.call_count)

        self.assertEqual({'1' : '1'}, notifier_1.fire.call_args[0][0])
        self.assertEqual(event, notifier_1.fire.call_args[0][1])

        self.assertEqual({'2' : '2'}, notifier_2.fire.call_args[0][0])
        self.assertEqual(event, notifier_2.fire.call_args[0][1])

    # -- event format tests ---------------------------------------------------

    def test_fire_repo_sync_started(self):
        # Setup
        notifier = mock.Mock()
        notifiers.NOTIFIER_FUNCTIONS['notifier_1'] = notifier.fire

        self.event_manager.create('notifier_1', {}, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        repo_id = 'test-repo'
        self.manager.fire_repo_sync_started(repo_id)

        # Verify
        self.assertEqual(1, notifier.fire.call_count)
        event = notifier.fire.call_args[0][1]

        self.assertEqual(event.event_type, event_data.TYPE_REPO_SYNC_STARTED)
        self.assertEqual(event.payload, {'repo_id' : repo_id})

    def test_fire_repo_sync_finished(self):
        # Setup
        notifier = mock.Mock()
        notifiers.NOTIFIER_FUNCTIONS['notifier_1'] = notifier.fire

        self.event_manager.create('notifier_1', {}, [event_data.TYPE_REPO_SYNC_FINISHED])

        # Test

        # The caller will retrieve and serialize the RepoSyncResult class,
        # so make up a fake dict here to simulate that.
        result = {'repo_id' : 'test-repo', 'result' : 'success'}
        self.manager.fire_repo_sync_finished(result)

        # Verify
        self.assertEqual(1, notifier.fire.call_count)
        event = notifier.fire.call_args[0][1]

        self.assertEqual(event.event_type, event_data.TYPE_REPO_SYNC_FINISHED)
        self.assertEqual(event.payload, result)

