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
from pulp.api import RepoApi
from pulp.model import Package

import time
import unittest
import logging
import os

class TestApi(unittest.TestCase):

    def setUp(self):
        self.rapi = RepoApi()
        
    def tearDown(self):
        RepoApi().clean()
        
    def test_create(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'http://example.com')
        assert(repo != None)
        
    def test_clean(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'http://example.com')
        self.rapi.clean()
        repos = self.rapi.repositories()
        assert(len(repos) == 0)
        
    def test_delete(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'http://example.com')
        repos = self.rapi.delete('some-id')
        assert(repos == None or len(repos) == 0)
        
    def test_repositories(self):
        repo = self.rapi.create('some-id','some name', 
            'i386', 'http://example.com')
        
        # list all the repos
        repos = self.rapi.repositories()
        found = False
        assert(len(repos) > 0)
        for r in repos:
            ## TODO: See if we can get dot notation here on id field
            if (r['id'] == 'some-id'):
                found = True

        assert(found)
    
    def test_repository(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'http://example.com')
        
        found = self.rapi.repository('some-id')
        assert(found != None)
        assert(found['id'] == 'some-id')
        
    def test_repo_packages(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'http://example.com')
        package = Package('test_repo_packages','test package')
        repo.packages[package.id] = package
        self.rapi.update(repo)
        
        found = self.rapi.repository('some-id')
        packages = found['packages']
        assert(packages != None)
        assert(packages['test_repo_packages'] != None)
        
    def test_sync(self):
        
        repo = self.rapi.create('some-id','some name', 'i386', 
                                'http://localhost/repo/f11-i386/')
        failed = False
        try:
            self.rapi.sync('invalid-id-not-found')
        except Exception:
            failed = True
        assert(failed)
        
        self.rapi.sync(repo.id)
        
        # Check that local storage has dir and rpms
        dirList = os.listdir(self.rapi.LOCAL_STORAGE + '/' + repo.id)
        assert(len(dirList) > 0)
        found = self.rapi.repository(repo.id)
        packages = found['packages']
        assert(packages != None)
        assert(len(packages) > 0)
        
        
if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.INFO)
    unittest.main()
