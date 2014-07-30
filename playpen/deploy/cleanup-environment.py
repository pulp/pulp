#!/usr/bin/env python

import argparse
import os

from utils import config_utils, os1_utils

# The nosetests command to run the integration tests
NOSETESTS_COMMAND = 'cd pulp-automation && nosetests -vs --with-xunit'

# Setup the CLI
description = 'Run integration tests using a deployed environment by deploy-environment.py'
parser = argparse.ArgumentParser(description=description)
parser.add_argument('--config', help='path to the configuration file produced by deploy-environment.py', required=True)
args = parser.parse_args()

config = config_utils.load_config(args.config)

print 'Authenticating with OS1...'
os1_auth = config.get(config_utils.CONFIG_OS1_CREDENTIALS, {})
os1 = os1_utils.OS1Manager(**os1_auth)
print 'Tearing down instances...'
os1.teardown_instances(config)
os.remove(args.config)
print 'Done!'
