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

    def create_repos(self):
        repo = self.rapi.create('test-id','test repo', \
            'i386', 'local:file:///opt/repo/sat-ng/')
        self.rapi.sync(repo.id)
        



if __name__ == '__main__':
    ll = LargeLoad()
    
    ll.create_repos()
    
    # ll.create_consumers()
    # ll.find_consumer()
    # ll.find_repo()
    # ll.find_consumers_with_package()
    
           
