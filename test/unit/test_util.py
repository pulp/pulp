#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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
import os
import sys
sys.path.append("../src")
from pulp.util import chunks
from pulp.util import get_rpm_information
from pulp.util import load_config

import time
import unittest
import logging

class TestUtil(unittest.TestCase):

    def test_getrpminfo(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data"
        info = get_rpm_information(datadir + '/pulp-test-package-0.2.1-1.fc11.x86_64.rpm')
        assert(info != None)
        assert(info['version'] == '0.2.1')
        assert(info['name'] == 'pulp-test-package')
        
    def test_chunks(self):
        list = range(1003)
        ck = chunks(list, 100)
        assert(len(ck) == 11)
        total = 0
        for chunk in ck:
            total = total + len(chunk)
        assert(total == 1003)

    def test_load_config(self):
        # Setup
        orig_file = os.path.abspath(os.path.dirname(__file__)) + '/../../etc/pulp/pulp.ini'
        override_file = os.path.abspath(os.path.dirname(__file__)) + '/../common/test-override-pulp.ini'
        
        # Test & Verify
        config = load_config(orig_file)
        self.assertEqual(config.get('paths', 'local_storage'), '/var/lib/pulp')

        config = load_config(override_file, config=config)
        self.assertEqual(config.get('paths', 'local_storage'), '/tmp/pulp')
       
        
if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.INFO)
    unittest.main()
