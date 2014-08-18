#!/usr/bin/env python

import argparse
import sys

from fabric.api import get, run, settings

from utils import config_utils, setup_utils

# The nosetests command to run the integration tests
NOSETESTS_COMMAND = 'cd pulp-automation && nosetests -vs --with-xunit --nologcapture'

# Setup the CLI
description = 'Run integration tests using a deployed environment by deploy-environment.py'
parser = argparse.ArgumentParser(description=description)
parser.add_argument('--config', help='path to the configuration file produced by deploy-environment.py', required=True)
parser.add_argument('--tests-destination', help='the location to place the nosetests.xml file on completion')
args = parser.parse_args()

config = config_utils.load_config(args.config)

flattened_config = config_utils.flatten_structure(config)
tester_config = filter(lambda conf: conf[setup_utils.ROLE] == setup_utils.PULP_TESTER_ROLE, flattened_config)[0]

with settings(host_string=tester_config[setup_utils.HOST_STRING], key_file=tester_config[setup_utils.PRIVATE_KEY]):
    test_result = run(NOSETESTS_COMMAND, warn_only=True)
    get('pulp-automation/nosetests.xml', args.tests_destination or tester_config['tests_destination'])

sys.exit(test_result.return_code)
