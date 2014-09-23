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

import mock
from pulp.server.db.model.dispatch import TaskStatus

from pulp.server.db.model.event import EventListener
from pulp.server.event import data as event_data
from pulp.server.event import http
from pulp.server.exceptions import InvalidValue, MissingResource
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.event import crud

import base

# -- test cases ---------------------------------------------------------------

class EventListenerManagerTests(base.PulpServerTests):

    def setUp(self):
        super(EventListenerManagerTests, self).setUp()

        self.manager = manager_factory.event_listener_manager()

    def clean(self):
        super(EventListenerManagerTests, self).clean()
        EventListener.get_collection().remove()

    def test_create(self):
        # Test
        created = self.manager.create(http.TYPE_ID, None, [event_data.TYPE_REPO_SYNC_STARTED])

        # Verify
        self.assertEqual(created['notifier_type_id'], http.TYPE_ID)
        self.assertEqual(created['notifier_config'], {})
        self.assertEqual(created['event_types'], [event_data.TYPE_REPO_SYNC_STARTED])

        all_event_listeners = list(EventListener.get_collection().find())
        self.assertEqual(1, len(all_event_listeners))

    def test_create_invalid_event_type(self):
        # Test
        try:
            self.manager.create(http.TYPE_ID, {}, ['foo'])
            self.fail()
        except InvalidValue, e:
            self.assertEqual(e.property_names, ['event_types'])

    def test_create_no_event_types(self):
        # Test
        try:
            self.manager.create(http.TYPE_ID, {}, None)
            self.fail()
        except InvalidValue, e:
            self.assertEqual(e.property_names, ['event_types'])

    def test_create_invalid_notifier_type(self):
        # Test
        try:
            self.manager.create('foo', {}, [event_data.TYPE_REPO_SYNC_STARTED])
            self.fail()
        except InvalidValue, e:
            self.assertEqual(e.property_names, ['notifier_type_id'])

    def test_delete(self):
        # Setup
        created = self.manager.create(http.TYPE_ID, {}, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        self.manager.delete(created['_id'])

        # Verify
        all_event_listeners = list(EventListener.get_collection().find())
        self.assertEqual(0, len(all_event_listeners))

    def test_delete_invalid_id(self):
        # Test
        try:
            self.manager.delete('foo')
            self.fail()
        except MissingResource, e:
            self.assertEqual(e.resources['event_listener'], 'foo')

    def test_get(self):
        # Setup
        created = self.manager.create(http.TYPE_ID, {}, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        gotten = self.manager.get(created['_id'])

        # Verify
        self.assertEqual(gotten['notifier_type_id'], http.TYPE_ID)

    def test_get_missing_listener(self):
        # Test
        try:
            self.manager.get('foo')
            self.fail()
        except MissingResource, e:
            self.assertEqual(e.resources['event_listener'], 'foo')

    def test_update(self):
        # Setup
        orig_config = {'k1' : 'v1', 'k2' : 'v2', 'k3' : 'v3'}
        created = self.manager.create(http.TYPE_ID, orig_config, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        updated = self.manager.update(created['_id'], {'k1' : 'vX', 'k2' : None}, [event_data.TYPE_REPO_SYNC_FINISHED])

        # Verify
        expected_config = {'k1' : 'vX', 'k3' : 'v3'}
        self.assertEqual(updated['notifier_config'], expected_config)
        self.assertEqual(updated['event_types'], [event_data.TYPE_REPO_SYNC_FINISHED])

    def test_update_invalid_listener(self):
        # Test
        try:
            self.manager.update('foo', {}, [event_data.TYPE_REPO_SYNC_STARTED])
            self.fail()
        except MissingResource, e:
            self.assertEqual(e.resources['event_listener'], 'foo')

    def test_update_invalid_types(self):
        # Setup
        created = self.manager.create(http.TYPE_ID, {}, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        try:
            self.manager.update(created['_id'], {}, [])
            self.fail()
        except InvalidValue, e:
            self.assertEqual(e.property_names, ['event_types'])

    def test_list(self):
        # Setup
        self.manager.create(http.TYPE_ID, {}, [event_data.TYPE_REPO_SYNC_STARTED])
        self.manager.create(http.TYPE_ID, {}, [event_data.TYPE_REPO_SYNC_FINISHED])

        # Test
        listeners = self.manager.list()

        # Verify
        self.assertEqual(2, len(listeners))

        listeners.sort(key=lambda x : x['event_types'])

        self.assertEqual(listeners[0]['event_types'], [event_data.TYPE_REPO_SYNC_FINISHED])
        self.assertEqual(listeners[1]['event_types'], [event_data.TYPE_REPO_SYNC_STARTED])

    def test_list_no_listeners(self):
        # Test
        listeners = self.manager.list() # should not error

        # Verify
        self.assertEqual(0, len(listeners))

    def test_validate_events(self):
        crud._validate_event_types(event_data.ALL_EVENT_TYPES)

    def test_validate_star(self):
        crud._validate_event_types(['*'])

    def test_validate_empty(self):
        self.assertRaises(InvalidValue, crud._validate_event_types, [])

# event tests ------------------------------------------------------------------


class EventTests(base.PulpServerTests):

    @mock.patch('celery.current_task')
    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.find_by_task_id')
    def test_event_instantiation(self, mock_find, mock_current_task):
        mock_current_task.request.id = 'fake_id'
        fake_task_status = TaskStatus('fake_id')
        mock_find.return_value = dict(fake_task_status)

        event_type = 'test_type'
        payload = 'test_payload'

        try:
            event = event_data.Event(event_type, payload)
        except Exception, e:
            self.fail(e.message)

        mock_find.assert_called_once_with('fake_id')
        self.assertEqual(dict(fake_task_status), event.call_report)

    @mock.patch('celery.current_task')
    @mock.patch('pulp.server.async.task_status_manager.TaskStatusManager.find_by_task_id')
    def test_data_call(self, mock_find, mock_current_task):
        mock_current_task.request.id = 'fake_id'
        fake_task_status = TaskStatus('fake_id')
        mock_find.return_value = dict(fake_task_status)
        data = {'event_type': 'test_type',
                'payload': 'test_payload',
                'call_report': dict(fake_task_status)}

        event = event_data.Event(data['event_type'], data['payload'])

        self.assertEqual(data, event.data())

    def test_no_current_task(self):
        event = event_data.Event('fake_type', {})

        self.assertTrue(event.call_report is None)

