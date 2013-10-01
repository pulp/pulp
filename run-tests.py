#!/usr/bin/env python
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
import subprocess
import sys
import argparse

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
    'client_admin/test/unit',
    'client_consumer/test/unit',
    'client_lib/test/unit',
    'common/test/unit',
    'devel/test/unit'
]

TESTS_NON_RHEL5 = [
    'nodes/test/unit',
    'server/test/unit'
]

#add ability to specify nosetest options
parser = argparse.ArgumentParser()
parser.add_argument('--xunit-file')
parser.add_argument('--with-xunit', action='store_true')
parser.add_argument('--disable-coverage', action='store_true')
parser.add_argument('-x', '--failfast', action='store_true')
arguments = parser.parse_args()

args = [
    'nosetests',
]

if not arguments.disable_coverage:
    args.extend(['--with-coverage',
    '--cover-html',
    '--cover-erase',
    '--cover-package',
    ','.join(PACKAGES)])


# don't run the server tests in RHEL5.
if sys.version_info >= (2, 6):
    args.extend(TESTS_NON_RHEL5)

args.extend(TESTS_ALL_PLATFORMS)

if arguments.failfast:
    args.extend(['-x'])
if arguments.with_xunit:
    args.extend(['--with-xunit', '--process-timeout=360'])
if arguments.xunit_file:
    args.extend(['--xunit-file', '../test/' + arguments.xunit_file])

#Call the test process
subprocess.call(args)
