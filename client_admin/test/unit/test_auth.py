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

from pulp.client.admin import auth
import base_builtins


class TestUserSearch(base_builtins.PulpClientTests):

    def setUp(self):
        super(TestUserSearch, self).setUp()
        self.user_section = auth.UserSection(self.context)

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


class TestAuthUser(unittest.TestCase):

    def test__prompt_password_given(self):
        """
        Test that when a password is given by the CLI, it is used correctly.
        """
        # Test that if a password is given by the CLI, this is the password
        mock_context = mock.MagicMock()
        mock_context.prompt.prompt_password.return_value = "prompt_password"
        self.user_section = auth.UserSection(mock_context)

        password = self.user_section._prompt_password("mock_login", "cli_password")
        self.assertEqual(password, "cli_password")

    def test__prompt_password_not_given(self):
        """
        Test that if a password is not given, the user is prompted for a password.
        """
        mock_context = mock.MagicMock()
        mock_context.prompt.prompt_password.return_value = "prompt_password"
        self.user_section = auth.UserSection(mock_context)

        password = self.user_section._prompt_password("mock_login")
        self.assertEqual(password, "prompt_password")

    def test__prompt_password_does_not_allow_empty_strings(self):
        """
        Test that if the password given by the user is an empty string, that the failure message is
        rendered and the user will be reprompted.
        """

        def get_pwd(*args):
            """
            Make sure that the loop does not break until there is a password.
            """
            if mock_context.prompt.prompt_password.call_count < 3:
                return ''
            else:
                return 'called_three_times'

        mock_context = mock.MagicMock()
        mock_context.prompt.prompt_password.side_effect = get_pwd
        self.user_section = auth.UserSection(mock_context)

        password = self.user_section._prompt_password('mock_user')
        self.assertEqual(password, 'called_three_times')
        self.assertEqual(3, mock_context.prompt.prompt_password.call_count)

    def test_create_user_with_kwargs(self):
        mock_context = mock.MagicMock()
        self.user_section = auth.UserSection(mock_context)

        self.user_section.create(login='mock_login', password='mock_password')
        mock_context.server.user.create.assert_called_once_with(
            'mock_login', 'mock_password', 'mock_login'
        )

    def test_create_user_no_password_kwarg(self):
        mock_context = mock.MagicMock()
        mock_context.prompt.prompt_password.return_value = 'user_entered_password'
        self.user_section = auth.UserSection(mock_context)

        self.user_section.create(login='mock_login')
        mock_context.server.user.create.assert_called_once_with(
            'mock_login', 'user_entered_password', 'mock_login'
        )

    def test_update_user_with_kwargs(self):
        mock_context = mock.MagicMock()
        self.user_section = auth.UserSection(mock_context)

        self.user_section.update(login='mock_login', password='mock_password')
        mock_context.server.user.update.assert_called_once_with(
            'mock_login', {'password': 'mock_password'}
        )

    def test_update_user_with_no_password_kwarg(self):
        mock_context = mock.MagicMock()
        mock_context.prompt.prompt_password.return_value = 'user_entered_password'
        self.user_section = auth.UserSection(mock_context)

        self.user_section.update(login='mock_login', p=True)
        mock_context.server.user.update.assert_called_once_with(
            'mock_login', {'p': True, 'password': 'user_entered_password'}
        )


class TestAuthRole(base_builtins.PulpClientTests):

    ROLE_ID = 'test-id'
    DISPLAY_NAME = 'test-display-name'
    DESCRIPTION = 'test-description'

    @mock.patch('pulp.bindings.auth.RoleAPI.update')
    def test_update(self, mock_binding):
        # Setup
        section = auth.RoleSection(self.context)
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
