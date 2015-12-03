#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import subprocess
import sys

from pulp.devel.test_runner import run_tests
from pulp.server.constants import PULP_DJANGO_SETTINGS_MODULE


# Find and eradicate any existing .pyc files, so they do not eradicate us!
PROJECT_DIR = os.path.dirname(__file__)
subprocess.call(['find', PROJECT_DIR, '-name', '*.pyc', '-delete'])

# These paths should all pass PEP-8 checks
paths_to_check = [PROJECT_DIR]

paths_to_ignore = ['common/pulp/common/backports/pkgutil.py']
os.environ['DJANGO_SETTINGS_MODULE'] = PULP_DJANGO_SETTINGS_MODULE

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
    'nodes/test/nodes_tests',
    'server/test/unit',
    'repoauth/test',
    'oid_validation/test',
    'devel/test/unit'
]

dir_safe_all_platforms = [os.path.join(os.path.dirname(__file__), x) for x in TESTS_ALL_PLATFORMS]
dir_safe_non_rhel5 = [os.path.join(os.path.dirname(__file__), x) for x in TESTS_NON_RHEL5]

tests_exit_code = run_tests(PACKAGES, dir_safe_all_platforms, dir_safe_non_rhel5,
                            flake8_paths=paths_to_check, flake8_exclude=paths_to_ignore)

sys.exit(tests_exit_code)
