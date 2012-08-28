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

import unittest

import mock

from pulp.bindings.event_listeners import EventListenerAPI

class TestEventListenerBindings(unittest.TestCase):
    def setUp(self):
        self.api = EventListenerAPI(mock.MagicMock())

    def test_path_exists(self):
        self.assertTrue(len(self.api.PATH) > 0)

    def test_list(self):
        ret = self.api.list()

        self.api.server.GET.assert_called_once_with(self.api.PATH)
        self.assertEqual(ret, self.api.server.GET.return_value.response_body)

    def test_create(self):
        values = {
            'notifier_type_id': 'email',
            'notifier_config': {'x': 'foo'},
            'event_types': ['repo-sync-started'],
        }

        ret = self.api.create(**values)

        self.api.server.POST.assert_called_once_with(self.api.PATH, values)
        self.assertEqual(ret, self.api.server.POST.return_value.response_body)

    def test_update(self):
        values = {
            'notifier_config': {'x': 'foo'},
            'event_types': ['repo-sync-started'],
        }

        ret = self.api.update('listener1', **values)

        self.api.server.PUT.assert_called_once_with(
            self.api.PATH + 'listener1/', values)
        self.assertEqual(ret, self.api.server.PUT.return_value)

    def test_partial_update(self):
        values = {
            'notifier_config': {'x': 'foo'},
        }

        ret = self.api.update('listener1', **values)

        self.api.server.PUT.assert_called_once_with(
            self.api.PATH + 'listener1/', values)
        self.assertEqual(ret, self.api.server.PUT.return_value)

    def test_delete(self):
        ret = self.api.delete('listener1')

        self.api.server.DELETE.assert_called_once_with(
            self.api.PATH + 'listener1/')
        self.assertEqual(ret, self.api.server.DELETE.return_value)

