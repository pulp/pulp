#!/usr/bin/env python

import argparse
import sys
import time
import traceback

from utils import os1_utils, setup_utils, config_utils


# Setup the CLI
description = 'Deploy a Pulp environment; this can be used in conjunction with the run-integrations-tests.py script'
parser = argparse.ArgumentParser(description=description)
parser.add_argument('--config', help='path to the configuration file to use to deploy the environment', nargs='+',
                    required=True)
parser.add_argument('--deployed-config', help='path to save the deployed instance configuration to; defaults to the'
                                              ' given config file with a json file extension.')
parser.add_argument('--test-branch', help='test suite branch to checkout on the tester instance')
parser.add_argument('--repo', help='path the the repository; will override repositories set in the configuration')
parser.add_argument('--no-teardown', action='store_true', help='do not clean up instances if an error occurs')
args = parser.parse_args()

print 'Parsing and validating the configuration file(s)...'
config = config_utils.parse_and_validate_config_files(args.config, args.repo, args.test_branch)
os1_auth = config.get(config_utils.CONFIG_OS1_CREDENTIALS, {})
print 'Done. \n\nAuthenticating with OS1...'
os1 = os1_utils.OS1Manager(**os1_auth)
print 'Done.\n'

try:
    # This metadata is attached to all instances to allow cleanup to find
    # stale instances made by this utility
    instance_metadata = {
        'pulp_instance': 'True',
        'build_time': str(time.time()),
    }
    print 'Deploying instances...'
    os1.build_instances(config, instance_metadata)

    print 'Applying role-specific configurations...'
    setup_utils.configure_instances(config)

    # Save the configuration for later cleanup
    if args.deployed_config is None:
        args.deployed_config = args.config[0] + '.json'
    config_utils.save_config(config, args.deployed_config)

    # Print out machine information and configuration
    print '\nThe following instances have been built:'
    for instance in config_utils.config_generator(config):
        print """
            Instance name: %(instance_name)s
            Role: %(role)s
            SSH: %(host_string)s
        """ % instance
    print 'The configuration file has been written to ' + args.deployed_config
except (Exception, KeyboardInterrupt), e:
    # Print exception message and quit
    exception_type, exception_value, exception_tb = sys.exc_info()
    print 'Error: %s - %s' % (exception_type, exception_value)
    traceback.print_tb(exception_tb)

    if not args.no_teardown:
        os1.teardown_instances(config)
    sys.exit(1)
