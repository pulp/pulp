#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import sys

from pulp.devel.test_runner import run_tests

# Find and eradicate any existing .pyc files, so they do not eradicate us!
PROJECT_DIR = os.path.dirname(__file__)
subprocess.call(['find', PROJECT_DIR, '-name', '*.pyc', '-delete'])

# Check for style
config_file = os.path.join(PROJECT_DIR, 'flake8.cfg')
# These paths should all pass PEP-8 checks
paths_to_check = [
    'server/pulp/server/agent/',
    'server/pulp/server/async/',
    'server/pulp/server/auth/',
    'server/pulp/server/content/',
    'server/pulp/server/tasks/',
    'server/test/unit/server/']
paths_to_check = [os.path.join(PROJECT_DIR, p) for p in paths_to_check]
command = ['flake8', '--config', config_file]
command.extend(paths_to_check)
flake8_exit_code = subprocess.call(command)

PACKAGES = [
    os.path.dirname(__file__),
    'pulp',
    'pulp_node',
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

tests_exit_code = run_tests(PACKAGES, dir_safe_all_platforms, dir_safe_non_rhel5)

sys.exit(flake8_exit_code or tests_exit_code)
