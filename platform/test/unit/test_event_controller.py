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
from pulp.server.compat import ObjectId

from pulp.server.event import data as event_data
from pulp.server.event import rest_api
from pulp.server.db.model.event import EventListener
from pulp.server.managers import factory as manager_factory

class EventCollectionControllerTests(base.PulpWebserviceTests):

    def clean(self):
        super(EventCollectionControllerTests, self).clean()

        EventListener.get_collection().remove()

    def test_post(self):
        # Setup
        params = {
            'notifier_type_id' : rest_api.TYPE_ID,
            'notifier_config' : {'a' : 'a'},
            'event_types' : [event_data.TYPE_REPO_SYNC_STARTED],
        }

        # Test
        status, body = self.post('/v2/events/', params)

        # Verify
        self.assertEqual(status, 201)
        self.assertEqual(body['notifier_type_id'], params['notifier_type_id'])
        self.assertEqual(body['notifier_config'], params['notifier_config'])
        self.assertEqual(body['event_types'], params['event_types'])

        db_listener = EventListener.get_collection().find_one({'id' : body['id']})
        self.assertTrue(db_listener is not None)
        self.assertEqual(db_listener['notifier_type_id'], params['notifier_type_id'])
        self.assertEqual(db_listener['notifier_config'], params['notifier_config'])
        self.assertEqual(db_listener['event_types'], params['event_types'])

        expected_href = '/v2/events/%s/' % body['id']
        self.assertEqual(body['_href'], expected_href)

    def test_get(self):
        # Setup
        manager = manager_factory.event_listener_manager()

        manager.create(rest_api.TYPE_ID, {}, [event_data.TYPE_REPO_SYNC_STARTED])
        manager.create(rest_api.TYPE_ID, {}, [event_data.TYPE_REPO_SYNC_STARTED])
        manager.create(rest_api.TYPE_ID, {}, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        status, body = self.get('/v2/events/')

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(3, len(body))

        for l in body:
            self.assertEqual(l['notifier_type_id'], rest_api.TYPE_ID)

class EventResourceControllerTests(base.PulpWebserviceTests):

    def clean(self):
        super(EventResourceControllerTests, self).clean()

        EventListener.get_collection().remove()

    def test_get(self):
        # Setup
        manager = manager_factory.event_listener_manager()

        created = manager.create(rest_api.TYPE_ID, {'a' : 'a'}, [event_data.TYPE_REPO_SYNC_STARTED])
        manager.create(rest_api.TYPE_ID, {'b' : 'b'}, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        status, body = self.get('/v2/events/%s/' % created['id'])

        # Verify
        self.assertEqual(200, status)
        self.assertEqual(body['notifier_config'], created['notifier_config'])

    def test_get_missing_resouce(self):
        # Test
        status, body = self.get('/v2/events/foo/')

        # Verify
        self.assertEqual(404, status)

    def test_delete(self):
        # Setup
        manager = manager_factory.event_listener_manager()
        created = manager.create(rest_api.TYPE_ID, {'a' : 'a'}, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        status, body = self.delete('/v2/events/%s/' % created['id'])

        # Verify
        self.assertEqual(200, status)

        deleted = EventListener.get_collection().find_one({'_id' : ObjectId(created['_id'])})
        self.assertTrue(deleted is None)

    def test_delete_missing_resource(self):
        # Test
        status, body = self.delete('/v2/events/foo/')

        # Verify
        self.assertEqual(404, status)

    def test_update_only_config(self):
        # Setup
        manager = manager_factory.event_listener_manager()
        created = manager.create(rest_api.TYPE_ID, {'a' : 'a', 'b' : 'b'}, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        new_config = {'a' : 'x', 'c' : 'c'}
        body = {
            'notifier_config' : new_config,
        }

        status, body = self.put('/v2/events/%s/' % created['id'], body)

        # Verify
        self.assertEqual(200, status)

        updated = EventListener.get_collection().find_one({'_id' : ObjectId(created['_id'])})
        expected_config = {'a' : 'x', 'b' : 'b', 'c' : 'c'}
        self.assertEqual(updated['notifier_config'], expected_config)

    def test_update_only_event_types(self):
        # Setup
        manager = manager_factory.event_listener_manager()
        created = manager.create(rest_api.TYPE_ID, {'a' : 'a', 'b' : 'b'}, [event_data.TYPE_REPO_SYNC_STARTED])

        # Test
        new_event_types = [event_data.TYPE_REPO_SYNC_FINISHED]
        body = {
            'event_types' : new_event_types,
        }

        status, body = self.put('/v2/events/%s/' % created['id'], body)

        # Verify
        self.assertEqual(200, status)

        updated = EventListener.get_collection().find_one({'_id' : ObjectId(created['_id'])})
        self.assertEqual(updated['event_types'], new_event_types)