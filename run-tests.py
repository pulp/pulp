#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import sys

from pulp.devel.test_runner import run_tests

# Find and eradicate any existing .pyc files, so they do not eradicate us!
PROJECT_DIR = os.path.dirname(__file__)
subprocess.call(['find', PROJECT_DIR, '-name', '*.pyc', '-delete'])

# These paths should all pass PEP-8 checks
paths_to_check = [
    'agent',
    'bindings',
    'client_lib/pulp/',
    'client_lib/test/data/extensions_loader_tests/individual_fail_extensions/init_error/'
    'pulp_cli.py',
    'client_lib/test/data/extensions_loader_tests/individual_fail_extensions/no_init_function/'
    'pulp_cli.py',
    'client_lib/test/data/extensions_loader_tests/valid_set/ext1/pulp_cli.py',
    'client_lib/test/data/extensions_loader_tests/valid_set/ext2/__init__.py',
    'client_lib/test/data/extensions_loader_tests/valid_set/ext2/pulp_cli.py',
    'client_lib/test/data/extensions_loader_tests/valid_set/ext3/pulp_cli.py',
    'client_lib/test/data/extensions_loader_tests/partial_fail_set/z_ext/pulp_cli.py',
    'client_lib/test/unit/client/commands/consumer/test_bind.py',
    'client_lib/test/unit/client/commands/repo/test_cudl.py',
    'client_lib/test/unit/client/commands/repo/test_status.py',
    'client_lib/test/unit/client/commands/repo/test_sync_publish.py',
    'client_lib/test/unit/client/commands/repo/test_upload.py',
    'client_lib/test/unit/client/commands/test_polling.py',
    'client_lib/test/unit/client/commands/test_unit.py',
    'client_lib/test/unit/client/extensions/test_exceptions.py',
    'client_lib/test/unit/client/test_launcher.py',
    'client_lib/test/unit/test_client_arg_utils.py',
    'client_lib/test/unit/test_client_framework_core.py',
    'client_lib/test/unit/test_client_upload_manager.py',
    'client_lib/test/unit/test_commands_consumer_content.py',
    'client_lib/test/unit/test_commands_consumer_content_schedule.py',
    'client_lib/test/unit/test_commands_criteria.py',
    'client_lib/test/unit/test_commands_history.py',
    'client_lib/test/unit/test_commands_importer_config.py',
    'client_lib/test/unit/test_commands_remove.py',
    'client_lib/test/unit/test_commands_repo_group.py',
    'client_lib/test/unit/test_commands_repo_query.py',
    'client_lib/test/unit/test_commands_schedule.py',
    'client_lib/test/unit/test_extensions_loader.py',
    'client_lib/test/unit/test_parsers.py',
    'client_lib/test/unit/test_validators.py',
    'repoauth/',
    'server/pulp/plugins',
    'server/pulp/server/agent/',
    'server/pulp/server/async/',
    'server/pulp/server/auth/',
    'server/pulp/server/common/',
    'server/pulp/server/content/',
    'server/pulp/server/db/',
    'server/pulp/server/event/',
    'server/pulp/server/maintenance/',
    'server/pulp/server/managers',
    'server/pulp/server/tasks/',
    'server/pulp/server/webservices/middleware/',
    'server/pulp/server/webservices/views/',
    'server/test/unit/plugins/',
    'server/test/unit/server/']

os.environ['DJANGO_SETTINGS_MODULE'] = 'pulp.server.webservices.settings'

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
    'repoauth/test',
    'devel/test/unit'
]

dir_safe_all_platforms = [os.path.join(os.path.dirname(__file__), x) for x in TESTS_ALL_PLATFORMS]
dir_safe_non_rhel5 = [os.path.join(os.path.dirname(__file__), x) for x in TESTS_NON_RHEL5]

tests_exit_code = run_tests(PACKAGES, dir_safe_all_platforms, dir_safe_non_rhel5,
                            flake8_paths=paths_to_check)

sys.exit(tests_exit_code)
