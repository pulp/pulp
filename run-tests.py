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
    'pulp_repo',
    'pulp_server_info',
    'pulp_tasks',
]

TESTS = 'platform/test/unit'
BUILTIN_TESTS = 'builtins/test/unit'
DEVEL_TESTS = 'pulp_devel/test/unit'

args = [
    'nosetests',
    '--with-coverage',
    '--cover-html',
    '--cover-erase',
    '--cover-package',
    ','.join(PACKAGES),
    TESTS,
    BUILTIN_TESTS,
    DEVEL_TESTS,
]

# don't run the server tests in RHEL5.
if sys.version_info < (2, 6):
    args.extend(['-e', 'server'])

#args.extend(['-e', 'server', '-v', '--collect-only'])

#add ability to specify nosetest options
parser = argparse.ArgumentParser()
parser.add_argument('--xunit-file')
parser.add_argument('--with-xunit', action='store_true')
arguments = parser.parse_args()

if arguments.with_xunit:
    args.extend(['--with-xunit', '--process-timeout=360'])
if arguments.xunit_file:
    args.extend(['--xunit-file', '../test/' + arguments.xunit_file])

print " ".join(args)
#Call the test process
subprocess.call(args)
