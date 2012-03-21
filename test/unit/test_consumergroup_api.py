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
import mock_plugins

from pulp.server.exceptions import PulpException
from pulp.server.agent import Agent

# Hack to use V2 repositories with V1 consumers.
import pulp.server.managers.factory as manager_factory
from pulp.server.db.model.gc_repository import Repo, RepoDistributor

# -- test cases ---------------------------------------------------------------------------

class TestConsumerApi(testutil.PulpAsyncTest):
    
    def setUp(self):
        super(testutil.PulpAsyncTest, self).setUp()
        mock_plugins.install()

        self.gc_repo_manager = manager_factory.repo_manager()
        self.gc_distributor_manager = manager_factory.repo_distributor_manager()
        self.dist_config = {'http': False,
                            'https': True,
                            'relative_url': 'test-repo'}
        
    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        self.consumer_group_api.clean()
        self.consumer_api.clean()
        self.repo_api.clean()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()

    def test_create_consumergroup(self, id = 'some-id'):
        cg = self.consumer_group_api.create(id, 'some description')
        found = self.consumer_group_api.consumergroup(id)
        assert(found is not None)
        assert(found['description'] == 'some description')
        assert(found['id'] == id)

        found = self.consumer_group_api.consumergroup('some-id-that-doesnt-exist')
        assert(found is None)
        
        # try creating another consumer group with same id
        try:
            cg = self.consumer_group_api.create(id, 'some description')
            assert(False)
        except PulpException:
            pass
        
    def test_create_consumergroup_with_consumerids(self, id = 'some-id'):
        try:
            cg = self.consumer_group_api.create(id, 'some description', consumerids=['con-test1','con-test2'])
            assert(False)
        except PulpException:
            pass    
        
        self.consumer_api.create('con-test1', 'con-test1')
        self.consumer_api.create('con-test2', 'con-test2')
        cg = self.consumer_group_api.create(id, 'some description', consumerids=['con-test1','con-test2'])
        assert('con-test1' in cg['consumerids'])
        assert('con-test2' in cg['consumerids'])
        
    def test_consumergroup_update(self, id = 'some-id'):
        cgs = self.consumer_group_api.consumergroups()
        assert(len(cgs) == 0)
        
        try:
            self.consumer_group_api.update(id, {'description':'some other description'})
            assert(False)
        except:
            pass
        
        self.consumer_group_api.create(id, 'some description')
        self.consumer_group_api.update(id, {'description':'some other description'})
        cgs = self.consumer_group_api.consumergroups()
        assert(len(cgs) == 1)
        
        try:
            self.consumer_group_api.update(id, {'foo':'bar'})
            assert(False)
        except:
            pass
        
    
    def test_add_consumer(self, id = 'groupid'):
        try:
            self.consumer_group_api.add_consumer(id, 'consumerid')
            assert(False)
        except:
            pass
        
        self.consumer_group_api.create(id, 'some description')
        try:
            self.consumer_group_api.add_consumer(id, 'consumerid')
            assert(False)
        except:
            pass
        self.consumer_api.create('consumerid', 'consumerid')
        self.consumer_group_api.add_consumer(id, 'consumerid')
        # try adding it again 
        self.consumer_group_api.add_consumer(id, 'consumerid')
        
        assert('consumerid' in self.consumer_group_api.consumers(id))
        
        
    def test_delete_consumer(self, id = 'groupid'):
        try:
            self.consumer_group_api.delete_consumer(id, 'consumerid')
            assert(False)
        except:
            pass
        
        self.consumer_api.create('consumerid', 'consumerid')
        self.consumer_group_api.create(id, 'some description', ['consumerid'])
        self.consumer_group_api.delete_consumer(id, 'consumerid')
        # deleting again should not result in error
        self.consumer_group_api.delete_consumer(id, 'consumerid')
        assert('consumerid' not in self.consumer_group_api.consumers(id))
        
    def test_bind_repo(self, id = 'groupid'):
        try:
            self.consumer_group_api.bind(id, 'test-repo')
            assert(False)
        except:
            pass
        
        self.consumer_api.create('consumerid1', 'consumerid1')
        self.consumer_api.create('consumerid2', 'consumerid2')
        self.consumer_group_api.create(id, 'some description', ['consumerid1', 'consumerid2'])
        
        try:
            self.consumer_group_api.bind(id, 'test-repo')
            assert(False)
        except:
            pass
        
        #self.repo_api.create(id='test-repo', name='test-repo', arch='i386')
        self.gc_repo_manager.create_repo('test-repo', 'Test Repo')
        self.gc_distributor_manager.add_distributor('test-repo', 'mock-distributor', self.dist_config, True, distributor_id='my_dist')
        
        self.consumer_group_api.bind(id, 'test-repo')
        c1 = self.consumer_api.consumer('consumerid1')
        c2 = self.consumer_api.consumer('consumerid2')
        assert('test-repo' in c1['repoids'])
        assert('test-repo' in c2['repoids'])
        
    def test_unbind_repo(self, id = 'groupid'):
        try:
            self.consumer_group_api.unbind(id, 'test-repo')
            assert(False)
        except:
            pass
        
        self.consumer_api.create('consumerid1', 'consumerid1')
        self.consumer_api.create('consumerid2', 'consumerid2')
        self.consumer_group_api.create(id, 'some description', ['consumerid1', 'consumerid2'])
        
        try:
            self.consumer_group_api.unbind(id, 'test-repo')
            assert(False)
        except:
            pass
        
        #self.repo_api.create(id='test-repo', name='test-repo', arch='i386')
        self.gc_repo_manager.create_repo('test-repo', 'Test Repo')
        self.gc_distributor_manager.add_distributor('test-repo', 'mock-distributor', self.dist_config, True, distributor_id='my_dist')
        
        self.consumer_group_api.bind(id, 'test-repo')
        self.consumer_group_api.unbind(id, 'test-repo')
        c1 = self.consumer_api.consumer('consumerid1')
        c2 = self.consumer_api.consumer('consumerid2')
        assert('test-repo' not in c1['repoids'])
        assert('test-repo' not in c2['repoids'])
        
    def test_add_consumer_with_conflicting_key_value(self, id = 'groupid'):
        self.consumer_api.create('consumerid', 'consumerid')
        self.consumer_api.add_key_value_pair('consumerid', 'key1', 'value1')
        
        self.consumer_group_api.create(id, 'some description')
        self.consumer_group_api.add_key_value_pair(id, 'key1', 'value2')
        
        try:
            self.consumer_group_api.add_consumer(id, 'consumerid')
            assert(False)
        except:
            pass

        self.consumer_api.delete_key_value_pair('consumerid', 'key1')
        self.consumer_group_api.add_consumer(id, 'consumerid')


    def test_package_install(self, cgid = 'A'):
        '''
        Test package install
        '''
        # Setup
        id = ('A','B')
        packages = ['zsh',]
        self.consumer_api.create(id[0], None)
        self.consumer_api.create(id[1], None)
        self.consumer_group_api.create(cgid, '')
        self.consumer_group_api.add_consumer(cgid, id[0])
        self.consumer_group_api.add_consumer(cgid, id[1])
        
        # Test
        job = self.consumer_group_api.installpackages(cgid, packages)
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

    def test_package_uninstall(self, cgid = 'A'):
        '''
        Test package uninstall
        '''
        # Setup
        id = ('A','B')
        packages = ['zsh',]
        self.consumer_api.create(id[0], None)
        self.consumer_api.create(id[1], None)
        self.consumer_group_api.create(cgid, '')
        self.consumer_group_api.add_consumer(cgid, id[0])
        self.consumer_group_api.add_consumer(cgid, id[1])

        # Test
        job = self.consumer_group_api.uninstallpackages(cgid, packages)
        self.assertTrue(job is not None)
        self.assertEqual(len(job.tasks), len(id))
        for task in job.tasks:
            task.run()

        # Verify
        for x in id:
            agent = Agent(x)
            pkgproxy = agent.Packages()
            calls = pkgproxy.uninstall.history()
            last = calls[-1]
            self.assertEqual(last.args[0], packages)

    def test_packagegrp_install(self, cgid = 'A'):
        '''
        Test package install
        '''
        # Setup
        id = ('A','B')
        packages = ['zsh',]
        self.consumer_api.create(id[0], None)
        self.consumer_api.create(id[1], None)
        self.consumer_group_api.create(cgid, '')
        self.consumer_group_api.add_consumer(cgid, id[0])
        self.consumer_group_api.add_consumer(cgid, id[1])

        grpid = 'test-group'

        # Test
        job = self.consumer_group_api.installpackagegroups(cgid, [grpid,])
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
            self.assertEqual(last.args[0], [grpid,])

    def test_packagegrp_uninstall(self, cgid = 'A'):
        '''
        Test package uninstall
        '''
        # Setup
        id = ('A','B')
        packages = ['zsh',]
        self.consumer_api.create(id[0], None)
        self.consumer_api.create(id[1], None)
        self.consumer_group_api.create(cgid, '')
        self.consumer_group_api.add_consumer(cgid, id[0])
        self.consumer_group_api.add_consumer(cgid, id[1])

        grpid = 'test-group'

        # Test
        job = self.consumer_group_api.uninstallpackagegroups(cgid, [grpid,])
        self.assertTrue(job is not None)
        self.assertEqual(len(job.tasks), len(id))
        for task in job.tasks:
            task.run()

        # Verify
        for x in id:
            agent = Agent(x)
            proxy = agent.PackageGroups()
            calls = proxy.uninstall.history()
            last = calls[-1]
            self.assertEqual(last.args[0], [grpid,])

    def test_consumergroup_with_i18n_id(self):
        cgid = id =  u'\u0938\u093e\u092f\u0932\u0940'
        self.test_add_consumer(id)
        self.clean()
        self.test_add_consumer_with_conflicting_key_value(id)
        self.clean()
        self.test_bind_repo(id)
        self.clean()
        self.test_consumergroup_update(id)
        self.clean()
        self.test_create_consumergroup(id)
        self.clean()
        self.test_create_consumergroup_with_consumerids(id)
        self.clean()
        self.test_delete_consumer(id)
        self.clean()
        self.test_package_install(cgid)
        self.clean()
        self.test_package_uninstall(cgid)
        self.clean()
        self.test_packagegrp_install(cgid)
        self.clean()
        self.test_packagegrp_uninstall(cgid)
        self.clean()
        self.test_unbind_repo(id)
        self.clean()