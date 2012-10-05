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

import os
import sys

import mock

import base_builtins

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../extensions/admin/'))
sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../extensions/consumer/'))

from pulp_admin_consumer import pulp_cli as admin_client
from pulp_consumer import pulp_cli as consumer_client


class TestConsumerSearch(base_builtins.PulpClientTests):

    def setUp(self):
        super(TestConsumerSearch, self).setUp()
        self.consumer_section = admin_client.AdminConsumerSection(self.context)

    def test_has_command(self):
        """
        Make sure the command was added to the section
        """
        self.assertTrue('search' in self.consumer_section.commands)

    @mock.patch('pulp.bindings.search.SearchAPI.search')
    def test_calls_search_api(self, mock_search):
        self.consumer_section.search(limit=20)
        self.assertEqual(mock_search.call_count, 1)
        mock_search.assert_called_once_with(limit=20)

    @mock.patch('pulp.bindings.search.SearchAPI.search', return_value=[1,2])
    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document')
    def test_calls_render(self, mock_render, mock_search):
        """
        the values 1 and 2 are just stand-in unique values that would actually
        be dict-like documents as returned by mongo. For this test, we just need
        to know that a value gets passed from one place to another.
        """
        self.consumer_section.search(limit=20)
        self.assertEqual(mock_render.call_count, 2)
        self.assertTrue(mock_render.call_args_list[0][0][0] in (1, 2))
        self.assertTrue(mock_render.call_args_list[1][0][0] in (1, 2))

    def test_invalid_input(self):
        self.assertRaises(ValueError, self.consumer_section.search, x=2)


class TestAdminConsumer(base_builtins.PulpClientTests):

    CONSUMER_ID = 'elvis'
    DISPLAY_NAME = 'The King'
    DESCRIPTION = 'The King, Elvis Presley'
    NOTES = {'age':'99', 'status':'dead'}

    @mock.patch('pulp.bindings.consumer.ConsumerAPI.update')
    def test_update(self, mock_binding):
        # Setup
        section = admin_client.AdminConsumerSection(self.context)
        options = {
            'consumer-id' : self.CONSUMER_ID,
            'display-name' : self.DISPLAY_NAME,
            'description' : self.DESCRIPTION,
            'note' : ['='.join(n) for n in self.NOTES.items()],
        }
        # Test
        section.update(**options)
        # Verify
        passed = dict(
            display_name=self.DISPLAY_NAME,
            description=self.DESCRIPTION,
            notes=self.NOTES)
        mock_binding.assert_called_with(self.CONSUMER_ID, passed)


class TestConsumerConsumer(base_builtins.PulpClientTests):

    CONSUMER_ID = 'elvis'
    DISPLAY_NAME = 'The King'
    DESCRIPTION = 'The King, Elvis Presley'
    NOTES = {'age':'99', 'status':'dead'}

    @mock.patch('pulp.bindings.consumer.ConsumerAPI.update')
    @mock.patch('pulp_consumer.pulp_cli.load_consumer_id', return_value=CONSUMER_ID)
    def test_update(self, mock_utils, mock_binding):
        # Setup
        command = consumer_client.UpdateCommand(self.context, '', '')
        options = {
            'display-name' : self.DISPLAY_NAME,
            'description' : self.DESCRIPTION,
            'note' : ['='.join(n) for n in self.NOTES.items()],
            }
        # Test
        command.update(**options)
        # Verify
        # Verify
        passed = dict(
            display_name=self.DISPLAY_NAME,
            description=self.DESCRIPTION,
            notes=self.NOTES)
        mock_binding.assert_called_with(self.CONSUMER_ID, passed)