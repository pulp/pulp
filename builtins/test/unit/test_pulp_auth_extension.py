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

from pulp_auth import pulp_cli as auth_client


class TestUserSearch(base_builtins.PulpClientTests):

    def setUp(self):
        super(TestUserSearch, self).setUp()
        self.user_section = auth_client.UserSection(self.context)

    def test_has_command(self):
        """
        Make sure the command was added to the section
        """
        self.assertTrue('search' in self.user_section.commands)

    @mock.patch('pulp.bindings.search.SearchAPI.search')
    def test_calls_search_api(self, mock_search):
        self.user_section.search(limit=20)
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
        self.user_section.search(limit=20)
        self.assertEqual(mock_render.call_count, 2)
        self.assertTrue(mock_render.call_args_list[0][0][0] in (1, 2))
        self.assertTrue(mock_render.call_args_list[1][0][0] in (1, 2))

    def test_invalid_input(self):
        self.assertRaises(ValueError, self.user_section.search, x=2)


class TestAuthUser(base_builtins.PulpClientTests):

    USER_LOGIN = 'test-login'
    PASSWORD = 'test-password'
    NAME = 'test-name'
    
    @mock.patch('pulp.bindings.auth.UserAPI.update')
    def test_update(self, mock_binding):
        # Setup
        section = auth_client.UserSection(self.context)
        options = {
            'login' : self.USER_LOGIN,
            'name' : self.NAME,
            'password' : self.PASSWORD,
        }
        # Test
        section.update(**options)
        # Verify
        passed = dict(
            password=self.PASSWORD,
            name=self.NAME)
        
        mock_binding.assert_called_with(self.USER_LOGIN, passed)
        

class TestAuthRole(base_builtins.PulpClientTests):

    ROLE_ID = 'test-id'
    DISPLAY_NAME = 'test-display-name'
    DESCRIPTION = 'test-description'
    
    @mock.patch('pulp.bindings.auth.RoleAPI.update')
    def test_update(self, mock_binding):
        # Setup
        section = auth_client.RoleSection(self.context)
        options = {
            'role-id' : self.ROLE_ID,
            'display-name' : self.DISPLAY_NAME,
            'description' : self.DESCRIPTION,
        }
        # Test
        section.update(**options)
        # Verify
        passed = dict(
            display_name=self.DISPLAY_NAME,
            description=self.DESCRIPTION)
        
        mock_binding.assert_called_with(self.ROLE_ID, passed)

