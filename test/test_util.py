#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jason Dobies
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
import sys
sys.path.append("../src")
from pulp.util import getRPMInformation

import time
import unittest
import logging

class TestUtil(unittest.TestCase):

    def test_getrpminfo(self):
        info = getRPMInformation('./data/pulp-test-package-0.2.1-1.fc11.x86_64.rpm')
        assert(info != None)
        assert(info['version'] == '0.2.1')
        assert(info['name'] == 'pulp-test-package')
        
        
if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.INFO)
    unittest.main()
