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

import sys
import os
import copy
try:
    from urlparse import parse_qs
except ImportError:
    # this was moved to the urlparse module in python 2.6
    from cgi import parse_qs

import mock

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)),
    '../../extensions/admin/'))

import base_builtins
from pulp_repo import pulp_cli

class TestRepoExtension(base_builtins.PulpClientTests):
    @property
    def REPO1(self):
        return copy.copy({
            'id' : 'repo-1',
            'display_name' : 'Repository 1',
            'importers' : ({'id' : 'imp-1'},),
            'distributors' : ({'id' : 'dist-1'},)
        })

    def setUp(self):
        super(TestRepoExtension, self).setUp()
        self.repo_section = pulp_cli.RepoSection(self.context)

    def test_list_no_data(self):
        """
        Test retrieving the list of repos when there are no repos present.
        """
        self.server_mock.request.return_value = (200, ())

        self.repo_section.list(summary=True, importers=False, distributors=False)

        self.assertEqual(len(self.recorder.lines), 4)

    def test_list(self):
        """
        Test retrieving the list of repos when there is at least one present.
        """
        self.server_mock.request.return_value = (200, (self.REPO1,))

        self.repo_section.list(summary=True, importers=False, distributors=False)

        self.assertTrue(len(self.recorder.lines) > 4)

    def test_list_with_importers(self):
        self.server_mock.request = mock.MagicMock(return_value = (200, ()))
        self.repo_section.list(summary=True, importers=True, distributors=False)

        self.assertEqual(self.server_mock.request.call_count, 1)
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertTrue(call_args[1].endswith('/repositories/?importers=True'))

    def test_list_without_importers(self):
        self.server_mock.request = mock.MagicMock(return_value = (200, ()))
        self.repo_section.list(summary=True, importers=False, distributors=False)

        self.assertEqual(self.server_mock.request.call_count, 1)
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertTrue(call_args[1].endswith('/repositories/'))

    def test_list_with_distributors(self):
        self.server_mock.request = mock.MagicMock(return_value = (200, ()))
        self.repo_section.list(summary=True, importers=False, distributors=True)

        self.assertEqual(self.server_mock.request.call_count, 1)
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertTrue(call_args[1].endswith('/repositories/?distributors=True'))

    def test_list_without_distributors(self):
        self.server_mock.request = mock.MagicMock(return_value = (200, ()))
        self.repo_section.list(summary=True, importers=False, distributors=False)

        self.assertEqual(self.server_mock.request.call_count, 1)
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertTrue(call_args[1].endswith('/repositories/'))

    def test_list_with_importers_and_distributors(self):
        self.server_mock.request = mock.MagicMock(return_value = (200, ()))
        self.repo_section.list(summary=True, importers=True, distributors=True)

        self.assertEqual(self.server_mock.request.call_count, 1)
        call_args = self.server_mock.request.call_args[0]
        self.assertEqual(call_args[0], 'GET')
        self.assertTrue(call_args[1].find('/repositories/?') >= 0)

        query_string = call_args[1][call_args[1].find('?') + 1:]
        query_params = parse_qs(query_string)
        for param in ('importers', 'distributors'):
            self.assertTrue(param in query_params)
            self.assertTrue(query_params[param][0])

