#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Mike McCune
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
from pulp.api import RepoApi
from pulp.api import PackageApi
from pulp.model import Package

import time
import logging
import unittest
import os


class LargeLoad(unittest.TestCase):
    
    """
    Util for loading large amounts of data through our API
    """
    def __init__(self):
        self.rapi = RepoApi()
        self.papi = PackageApi()

    def create_repos(self):
        self.rapi.clean()
        repo = self.rapi.create('test-id','test repo', \
            'i386', 'local:file:///opt/repo/misc-packages/')
        self.rapi.sync(repo.id)
        print "Repos Created"
        



console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
logging.getLogger('pulp.api').addHandler(console)

ll = LargeLoad()
ll.create_repos()
repos = ll.rapi.repositories()
packages = ll.papi.packages()

print "number of repos: %s" % len(list(repos))
print "number of packages: %s" % len(packages)
# ll.create_consumers()
# ll.find_consumer()
# ll.find_repo()
# ll.find_consumers_with_package()

           
