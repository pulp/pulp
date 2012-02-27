#!/usr/bin/env python

import os
import sys
from pulp.gc_client.api.server import PulpConnection
from pulp.gc_client.api.server import DuplicateResourceException, PermissionsException
from pulp.gc_client.api.bindings import Bindings
from pulp.gc_client.api.repository import RepositoryAPI
import time


class RepoBindingsTest(object):
    
    def __init__(self):
        pc = PulpConnection(host="localhost", username='admin', password='admin')
        self.bindings = Bindings(pc)
        
    def clean(self):
        print "Cleaning all repositories..."
        for repo in self.bindings.repo.repositories().response_body:
            self.bindings.repo.delete(repo['id'])
        
    def test_list(self):
        repoid1 = "test-repo1"
        repoid2 = "test-repo2"
        repo1 = self.bindings.repo.create(id=repoid1, display_name=repoid1, description=repoid1, notes={})
        repo2 = self.bindings.repo.create(id=repoid2, display_name=repoid2, description=repoid2, notes={})
        assert(repo1 is not None)
        assert(repo2 is not None)
        print "listing all repositories..."
        repos = self.bindings.repo.repositories().response_body
        assert(len(repos)==2)
        
    def test_create(self, repoid):
        print "Will create repository [%s]..." % repoid
        repo = self.bindings.repo.create(id=repoid, display_name=repoid, description=repoid, notes={}).response_body
        assert(repo is not None)
        try:
            self.bindings.repo.create(id=repoid, display_name=repoid, description=repoid, notes={})
        except DuplicateResourceException, e:
            print e
        
if __name__ == "__main__":
    repo_bindings = RepoBindingsTest()
    repo_bindings.clean()
    repo_bindings.test_list()
    repo_bindings.clean()
    repo_bindings.test_create("test-repo")
