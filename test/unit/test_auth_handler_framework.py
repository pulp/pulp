#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
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
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp.repo_auth.auth_handler_framework as auth_framework


# Functions that simulate plugins so we can influence the outcome
def fail(request):
    return False

def win(request):
    return True

class MockFunctionsTests(testutil.PulpAsyncTest):

    def test_handle_fail_required_pass_optional(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = [win, win, fail]
        auth_framework.OPTIONAL_PLUGINS = [win]

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.HTTP_UNAUTHORIZED, http_code)

    def test_handle_pass_required_fail_optional(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = [win, win]
        auth_framework.OPTIONAL_PLUGINS = [fail, fail, fail]

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.HTTP_UNAUTHORIZED, http_code)

    def test_handle_pass_no_optional(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = [win]
        auth_framework.OPTIONAL_PLUGINS = []

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.OK, http_code)

    def test_handle_fail_no_optional(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = [fail]
        auth_framework.OPTIONAL_PLUGINS = []

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.HTTP_UNAUTHORIZED, http_code)

    def test_handle_no_plugins(self):
        # Setup
        auth_framework.REQUIRED_PLUGINS = []
        auth_framework.OPTIONAL_PLUGINS = []

        request = MockRequest()

        # Test
        http_code = auth_framework._handle(request)

        self.assertEqual(auth_framework.apache.OK, http_code)


class MockRequest(object):

    def add_common_vars(self):
        pass

    def log_error(self, message):
        pass
