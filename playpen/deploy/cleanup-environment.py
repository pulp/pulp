#!/usr/bin/python

import os

from utils import config_utils, os1_utils

# The nosetests command to run the integration tests
NOSETESTS_COMMAND = 'cd pulp-automation && nosetests -vs --with-xunit'

config = config_utils.load_config()

print 'Authenticating with OS1...'
os1_auth = config.get(config_utils.CONFIG_OS1_CREDENTIALS, {})
os1 = os1_utils.OS1Manager(**os1_auth)
print 'Tearing down instances...'
os1.teardown_instances(config)
os.remove(config_utils.DEFAULT_FILE_PATH)
print 'Done!'
