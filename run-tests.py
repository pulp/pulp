#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
import subprocess

from pulp.devel.test_runner import run_tests

# Find and eradicate any existing .pyc files, so they do not eradicate us!
PROJECT_DIR = os.path.dirname(__file__)
subprocess.call(['find', PROJECT_DIR, '-name', '*.pyc', '-delete'])

PACKAGES = [
    'pulp',
    'pulp_admin_auth',
    'pulp_admin_consumer',
    'pulp_consumer',
    'pulp_node',
    'pulp_repo',
    'pulp_server_info',
    'pulp_tasks',
]

TESTS_ALL_PLATFORMS = [
    'agent/test/unit',
    'bindings/test/unit',
    'client_consumer/test/unit',
    'client_lib/test/unit',
    'common/test/unit'
]

TESTS_NON_RHEL5 = [
    'client_admin/test/unit',
    'nodes/test/unit',
    'server/test/unit',
    'devel/test/unit'
]

dir_safe_all_platforms = [os.path.join(os.path.dirname(__file__), x) for x in TESTS_ALL_PLATFORMS]
dir_safe_non_rhel5 = [os.path.join(os.path.dirname(__file__), x) for x in TESTS_NON_RHEL5]

run_tests(PACKAGES, dir_safe_all_platforms, dir_safe_non_rhel5)
