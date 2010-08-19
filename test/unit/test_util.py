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
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.insert(0, srcdir)

from pulp.util import chunks
from pulp.util import get_rpm_information
from pulp.util import get_repo_packages
from pulp.util import get_repo_package
import time
import unittest
import logging

logging.root.setLevel(logging.ERROR)

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

    def test_get_repo_packages(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir_a = my_dir + "/data/sameNEVRA_differentChecksums/A/repo/"
        packages = get_repo_packages(datadir_a)
        self.assertTrue(len(packages) > 0)
        p = packages[0]
        self.assertTrue(p.name != None)
        
    def test_get_repo_package(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir_a = my_dir + "/data/sameNEVRA_differentChecksums/A/repo/"
        package = get_repo_package(datadir_a, 
                      'pulp-test-package-same-nevra-0.1.0-1.x86_64.rpm')
        self.assertNotEquals(package, None)
        self.assertNotEquals(package.name, None)
        
        
if __name__ == '__main__':
    unittest.main()
