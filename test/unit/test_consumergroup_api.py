#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.exceptions import PulpException
from pulp.server.agent import Agent


# -- test cases ---------------------------------------------------------------------------

class TestConsumerApi(testutil.PulpAsyncTest):

    def test_create_consumergroup(self):
        cg = self.consumer_group_api.create('some-id', 'some description')
        found = self.consumer_group_api.consumergroup('some-id')
        assert(found is not None)
        assert(found['description'] == 'some description')
        assert(found['id'] == 'some-id')

        found = self.consumer_group_api.consumergroup('some-id-that-doesnt-exist')
        assert(found is None)
        
        # try creating another consumer group with same id
        try:
            cg = self.consumer_group_api.create('some-id', 'some description')
            assert(False)
        except PulpException:
            pass
        
    def test_create_consumergroup_with_consumerids(self):
        try:
            cg = self.consumer_group_api.create('some-id', 'some description', consumerids=['con-test1','con-test2'])
            assert(False)
        except PulpException:
            pass    
        
        self.consumer_api.create('con-test1', 'con-test1')
        self.consumer_api.create('con-test2', 'con-test2')
        cg = self.consumer_group_api.create('some-id', 'some description', consumerids=['con-test1','con-test2'])
        assert('con-test1' in cg['consumerids'])
        assert('con-test2' in cg['consumerids'])
        
    def test_consumergroup_update(self):
        cgs = self.consumer_group_api.consumergroups()
        assert(len(cgs) == 0)
        
        try:
            self.consumer_group_api.update('some-id', {'description':'some other description'})
            assert(False)
        except:
            pass
        
        self.consumer_group_api.create('some-id', 'some description')
        self.consumer_group_api.update('some-id', {'description':'some other description'})
        cgs = self.consumer_group_api.consumergroups()
        assert(len(cgs) == 1)
        
        try:
            self.consumer_group_api.update('some-id', {'foo':'bar'})
            assert(False)
        except:
            pass
        
    
    def test_add_consumer(self):
        try:
            self.consumer_group_api.add_consumer('groupid', 'consumerid')
            assert(False)
        except:
            pass
        
        self.consumer_group_api.create('groupid', 'some description')
        try:
            self.consumer_group_api.add_consumer('groupid', 'consumerid')
            assert(False)
        except:
            pass
        self.consumer_api.create('consumerid', 'consumerid')
        self.consumer_group_api.add_consumer('groupid', 'consumerid')
        # try adding it again 
        self.consumer_group_api.add_consumer('groupid', 'consumerid')
        
        assert('consumerid' in self.consumer_group_api.consumers('groupid'))
        
        
    def test_delete_consumer(self):
        try:
            self.consumer_group_api.delete_consumer('groupid', 'consumerid')
            assert(False)
        except:
            pass
        
        self.consumer_api.create('consumerid', 'consumerid')
        self.consumer_group_api.create('groupid', 'some description', ['consumerid'])
        self.consumer_group_api.delete_consumer('groupid', 'consumerid')
        # deleting again should not result in error
        self.consumer_group_api.delete_consumer('groupid', 'consumerid')
        assert('consumerid' not in self.consumer_group_api.consumers('groupid'))
        
    def test_bind_repo(self):
        try:
            self.consumer_group_api.bind('groupid', 'test-repo')
            assert(False)
        except:
            pass
        
        self.consumer_api.create('consumerid1', 'consumerid1')
        self.consumer_api.create('consumerid2', 'consumerid2')
        self.consumer_group_api.create('groupid', 'some description', ['consumerid1', 'consumerid2'])
        
        try:
            self.consumer_group_api.bind('groupid', 'test-repo')
            assert(False)
        except:
            pass
        
        self.repo_api.create(id='test-repo', name='test-repo', arch='i386')
        
        self.consumer_group_api.bind('groupid', 'test-repo')
        c1 = self.consumer_api.consumer('consumerid1')
        c2 = self.consumer_api.consumer('consumerid2')
        assert('test-repo' in c1['repoids'])
        assert('test-repo' in c2['repoids'])
        
    def test_unbind_repo(self):
        try:
            self.consumer_group_api.unbind('groupid', 'test-repo')
            assert(False)
        except:
            pass
        
        self.consumer_api.create('consumerid1', 'consumerid1')
        self.consumer_api.create('consumerid2', 'consumerid2')
        self.consumer_group_api.create('groupid', 'some description', ['consumerid1', 'consumerid2'])
        
        try:
            self.consumer_group_api.unbind('groupid', 'test-repo')
            assert(False)
        except:
            pass
        
        self.repo_api.create(id='test-repo', name='test-repo', arch='i386')
        
        self.consumer_group_api.bind('groupid', 'test-repo')
        self.consumer_group_api.unbind('groupid', 'test-repo')
        c1 = self.consumer_api.consumer('consumerid1')
        c2 = self.consumer_api.consumer('consumerid2')
        assert('test-repo' not in c1['repoids'])
        assert('test-repo' not in c2['repoids'])
        
    def test_add_consumer_with_conflicting_key_value(self):
        self.consumer_api.create('consumerid', 'consumerid')
        self.consumer_api.add_key_value_pair('consumerid', 'key1', 'value1')
        
        self.consumer_group_api.create('groupid', 'some description')
        self.consumer_group_api.add_key_value_pair('groupid', 'key1', 'value2')
        
        try:
            self.consumer_group_api.add_consumer('groupid', 'consumerid')
            assert(False)
        except:
            pass

        self.consumer_api.delete_key_value_pair('consumerid', 'key1')
        self.consumer_group_api.add_consumer('groupid', 'consumerid')


    def test_package_install(self):
        '''
        Test package install
        '''
        # Setup
        id = ('A','B')
        packages = ['zsh',]
        self.consumer_api.create(id[0], None)
        self.consumer_api.create(id[1], None)
        self.consumer_group_api.create(id[0], '')
        self.consumer_group_api.add_consumer(id[0], id[0])
        self.consumer_group_api.add_consumer(id[0], id[1])
        
        # Test
        job = self.consumer_group_api.installpackages(id[0], packages)
        self.assertTrue(job is not None)
        self.assertEqual(len(job.tasks), len(id))
        for task in job.tasks:
            task.run()
            
        # Verify
        for x in id:
            agent = Agent(x)
            pkgproxy = agent.Packages()
            calls = pkgproxy.install.history()
            last = calls[-1]
            self.assertEqual(last.args[0], packages)

    def test_packagegrp_install(self):
        '''
        Test package install
        '''
        # Setup
        id = ('A','B')
        packages = ['zsh',]
        self.consumer_api.create(id[0], None)
        self.consumer_api.create(id[1], None)
        self.consumer_group_api.create(id[0], '')
        self.consumer_group_api.add_consumer(id[0], id[0])
        self.consumer_group_api.add_consumer(id[0], id[1])

        repoid = 'test-repo'
        grpid = 'test-group'
        grpname = 'test-group'
        self.repo_api.create(repoid, 'Test Repo', 'noarch')
        group = self.repo_api.create_packagegroup(repoid, grpid, grpname, '')
        package = testutil.create_package(self.package_api, packages[0])
        self.repo_api.add_package(repoid, [package["id"]])
        self.repo_api.add_packages_to_group(repoid, grpid, [packages[0]], gtype="default")

        # Test
        job = self.consumer_group_api.installpackagegroups(id[0], [grpname,])
        self.assertTrue(job is not None)
        self.assertEqual(len(job.tasks), len(id))
        for task in job.tasks:
            task.run()

        # Verify
        for x in id:
            agent = Agent(x)
            proxy = agent.PackageGroups()
            calls = proxy.install.history()
            last = calls[-1]
            self.assertEqual(last.args[0], [grpname,])