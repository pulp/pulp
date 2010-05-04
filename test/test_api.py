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
from api.api import RepoApi

import time
import unittest
import logging

class TestApi(unittest.TestCase):

    def setUp(self):
        print('Setting up test environment')

    def test_create(self):
        rapi = RepoApi()
        repo = rapi.create('some-id','some name', 'i386', 'http://example.com')
        assert(repo != None)
        
    def test_repositories(self):
        rapi = RepoApi()
        repo = rapi.create('some-id','some name', 'i386', 'http://example.com')
        
        # list all the repos
        repos = rapi.repositories()
        found = False
        assert(len(repos) > 0)
        for r in repos:
            ## TODO: See if we can get dot notation here on id field
            if (r['id'] == 'some-id'):
                found = True

        assert(found)
            


if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.INFO)

    unittest.main()
