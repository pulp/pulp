#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
import sys
import unittest

srcdir = os.path.abspath(os.path.dirname(__file__)) + '/../src/'
sys.path.insert(0, srcdir)

import pulp.repo_auth.auth_handler_framework as auth_framework


# Functions that simulate plugins so we can influence the outcome
def fail(request, log_func):
    return False

def win(request, log_func):
    return True


class MockFunctionsTests(unittest.TestCase):

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
