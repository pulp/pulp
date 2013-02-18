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
from pprint import pformat

import mock

from pulp.client.commands.consumer import bind as consumer_bind
from pulp.client.commands.options import OPTION_CONSUMER_ID, OPTION_REPO_ID
from pulp.server.compat import json

import base


class InstantiationTests(unittest.TestCase):

    def setUp(self):
        self.mock_context = mock.MagicMock()

    def tearDown(self):
        self.mock_context = None

    def test_bind(self):
        try:
            consumer_bind.ConsumerBindCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_unbind(self):
        try:
            consumer_bind.ConsumerUnbindCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))


class BindCommandTests(base.PulpClientTests):

    def setUp(self):
        super(BindCommandTests, self).setUp()
        self.command = consumer_bind.ConsumerBindCommand(self.context)

    def test_structure(self):
        found_options = set(self.command.options)
        expected_options = set((OPTION_CONSUMER_ID, OPTION_REPO_ID, consumer_bind.OPTION_DISTRIBUTOR_ID))
        self.assertEqual(found_options, expected_options)

        self.assertEqual(self.command.run, self.command.method)
        self.assertEqual(self.command.name, 'bind')

    def test_bind(self):
        self.server_mock.request.return_value = 201, {}

        kwargs = {
            OPTION_CONSUMER_ID.keyword: 'test-consumer',
            OPTION_REPO_ID.keyword: 'test-repo',
            consumer_bind.OPTION_DISTRIBUTOR_ID.keyword: 'yum-distributor'}

        self.command.run(**kwargs)

        self.assertEqual(self.server_mock.request.call_count, 1)
        self.assertEqual(self.server_mock.request.call_args[0][0], 'POST')

        url = self.server_mock.request.call_args[0][1]

        self.assertTrue(url.find('test-consumer') > 0)

        body = json.loads(self.server_mock.request.call_args[0][2])

        self.assertEqual(body['repo_id'], 'test-repo')
        self.assertEqual(body['distributor_id'], 'yum-distributor')


class UnbindCommandTests(base.PulpClientTests):

    def setUp(self):
        super(UnbindCommandTests, self).setUp()
        self.command = consumer_bind.ConsumerUnbindCommand(self.context)

    def test_structure(self):
        found_options = set(self.command.options)
        expected_options = set((OPTION_CONSUMER_ID, OPTION_REPO_ID, consumer_bind.OPTION_DISTRIBUTOR_ID, consumer_bind.FLAG_FORCE))
        self.assertEqual(found_options, expected_options)

        self.assertEqual(self.command.run, self.command.method)

        self.assertEqual(self.command.name, 'unbind')

    def test_unbind(self):
        self.server_mock.request.return_value = 201, {}

        kwargs = {
            OPTION_CONSUMER_ID.keyword: 'test-consumer',
            OPTION_REPO_ID.keyword: 'test-repo',
            consumer_bind.OPTION_DISTRIBUTOR_ID.keyword: 'yum-distributor',
            consumer_bind.FLAG_FORCE.keyword: None}

        self.command.run(**kwargs)

        self.assertEqual(self.server_mock.request.call_count, 1)
        self.assertEqual(self.server_mock.request.call_args[0][0], 'DELETE')

        url = self.server_mock.request.call_args[0][1]

        self.assertTrue(url.find('test-consumer') > 0)
        self.assertTrue(url.find('test-repo') > 0)
        self.assertTrue(url.find('yum-distributor') > 0)

