#!/usr/bin/python

import argparse
import sys
import time

from utils import os1_utils, setup_utils, config_utils


# Setup the CLI
description = 'Deploy a Pulp environment; this can be used in conjunction with the run-integrations-tests.py script'
parser = argparse.ArgumentParser(description=description)
parser.add_argument('--config', help='Path to the configuration file to use to deploy the environment', nargs='+')
parser.add_argument('--repo', help='Path the the repository; will override repositories set in the configuration')
parser.add_argument('--no-teardown', action='store_true', help='do not clean up instances if an error occurs')
args = parser.parse_args()

print 'Parsing and validating the configuration file(s)...'
config = config_utils.parse_and_validate_config_files(args.config, args.repo)
os1_auth = config.get(config_utils.CONFIG_OS1_CREDENTIALS, {})
print 'Done. \n\nAuthenticating with OS1...'
os1 = os1_utils.OS1Manager(**os1_auth)
print 'Done.\n'

print repr(config)

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
    config_utils.save_config(config)
except Exception, e:
    # Print exception message and quit
    print 'Error: %s - %s' % (type(e).__name__, e)

    if not args.no_teardown:
        os1.teardown_instances(config)
    sys.exit(1)
