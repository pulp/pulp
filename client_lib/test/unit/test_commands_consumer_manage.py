# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import unittest

import mock

from pulp.client.commands.consumer import manage as consumer_manage
from pulp.client.commands.options import (
    OPTION_CONSUMER_ID, OPTION_NAME, OPTION_DESCRIPTION, OPTION_NOTES)
from pulp.common.compat import json
from pulp.devel.unit import base


class InstantiationTests(unittest.TestCase):

    def setUp(self):
        self.mock_context = mock.MagicMock()

    def tearDown(self):
        self.mock_context = None

    def test_register(self):
        try:
            consumer_manage.ConsumerRegisterCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_unregister(self):
        try:
            consumer_manage.ConsumerUnregisterCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_update(self):
        try:
            consumer_manage.ConsumerUpdateCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))


class UnregisterCommand(base.PulpClientTests):

    def setUp(self):
        super(UnregisterCommand, self).setUp()
        self.command = consumer_manage.ConsumerUnregisterCommand(self.context)

    def test_structure(self):
        found_options = set(self.command.options)
        expected_options = set((OPTION_CONSUMER_ID,))
        self.assertEqual(found_options, expected_options)

        self.assertEqual(self.command.method, self.command.run)
        self.assertEqual(self.command.name, 'unregister')

    def test_unregister(self):
        self.server_mock.request.return_value = 201, {}

        kwargs = {OPTION_CONSUMER_ID.keyword: 'test-consumer'}

        self.command.run(**kwargs)

        self.assertEqual(self.server_mock.request.call_count, 1)
        self.assertEqual(self.server_mock.request.call_args[0][0], 'DELETE')

        url = self.server_mock.request.call_args[0][1]

        self.assertTrue(url.find('test-consumer') > 0)


class UpdateCommandTests(base.PulpClientTests):

    def setUp(self):
        super(UpdateCommandTests, self).setUp()
        self.command = consumer_manage.ConsumerUpdateCommand(self.context)

    def test_structure(self):
        found_options = set(self.command.options)
        expected_options = set((OPTION_CONSUMER_ID, OPTION_NAME, OPTION_DESCRIPTION, OPTION_NOTES))
        self.assertEqual(found_options, expected_options)

        self.assertEqual(self.command.method, self.command.run)
        self.assertEqual(self.command.name, 'update')

    def test_update(self):
        self.server_mock.request.return_value = 201, {}

        kwargs = {OPTION_CONSUMER_ID.keyword: 'test-consumer',
                  OPTION_NAME.keyword: 'Test Consumer',
                  OPTION_DESCRIPTION.keyword: 'Consumer for testing',
                  OPTION_NOTES.keyword: {'a': 'a', 'b': 'b'}}

        self.command.run(**kwargs)

        self.assertEqual(self.server_mock.request.call_count, 1)
        self.assertEqual(self.server_mock.request.call_args[0][0], 'PUT')

        url = self.server_mock.request.call_args[0][1]

        self.assertTrue(url.find('test-consumer') > 0)

        body = json.loads(self.server_mock.request.call_args[0][2])

        self.assertEqual(body['delta']['display_name'], 'Test Consumer')
        self.assertEqual(body['delta']['description'], 'Consumer for testing')
        self.assertEqual(body['delta']['notes'], {'a': 'a', 'b': 'b'})

