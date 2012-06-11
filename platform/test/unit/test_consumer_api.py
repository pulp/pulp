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

from pulp.server.agent import Agent
from pulp.common.bundle import Bundle
from pulp.server.exceptions import PulpException
from pulp.server.auth.certificate import Certificate

# Hack to use V2 repositories with V1 consumers.
import pulp.server.managers.factory as manager_factory
from pulp.server.db.model.gc_repository import Repo, RepoDistributor


# default capabilities
CAPABILITIES = dict(heartbeat=True, bind=True)

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
        super(testutil.PulpAsyncTest, self).clean()

        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()

    # -- create test cases ---------------------------------------------------------------
    
    def test_registrations(self):
        '''
        Tests the happy path of registration.
        '''
        
        # Setup
        id = 'test-consumer'
        description = 'my excellent description'
        created = self.consumer_api.create(id, description, CAPABILITIES)
        
        # Test
        all = self.consumer_api.consumers()
        fetched = self.consumer_api.consumer(id)
        
        # Verify
        self.assertEqual(len(all), 1)
        self.assertEqual(all[0]['id'], fetched['id'])
        self.assertEqual(description, fetched['description'])
        self.assertTrue(Bundle.hasboth(created['certificate']))
        self.assertEqual(CAPABILITIES, fetched['capabilities'])
        self.assertTrue(Bundle.hascrt(fetched['certificate']))
        self.assertFalse(Bundle.haskey(fetched['certificate']))
        crt = Certificate()
        crt.update(str(fetched['certificate']))
        subject = crt.subject()
        self.assertEqual(id, subject.get('CN', None))
        
    def test_consumer_delete(self):
        # Setup
        id = 'delete-me'
        self.consumer_api.create(id, '')
        self.assertTrue(self.consumer_api.consumer(id) is not None)

        # Test
        self.consumer_api.delete(id)

        # Verify
        self.assertTrue(self.consumer_api.consumer(id) is None)


    # -- bind test cases -----------------------------------------------------------------

    def test_bind(self):
        '''
        Tests the happy path of binding a consumer to a repo.
        '''

        # Setup
        #self.repo_api.create('test-repo', 'Test Repo', 'noarch')
        self.gc_repo_manager.create_repo('test-repo', 'Test Repo')
        self.gc_distributor_manager.add_distributor('test-repo', 'mock-distributor', self.dist_config, True, distributor_id='my_dist')
        
        self.consumer_api.create('test-consumer', None, CAPABILITIES)

        # Test
        returned_bind_data = self.consumer_api.bind('test-consumer', 'test-repo')

        # Verify

        # Database
        consumer = self.consumer_api.consumer('test-consumer')
        self.assertTrue(consumer is not None)
        self.assertTrue('test-repo' in consumer['repoids'])

        # Bind data validation
        def verify_bind_data(bind_data):
            self.assertTrue(bind_data is not None)

            # Verify repo
            data_repo = bind_data['repo']
            self.assertTrue(data_repo is not None)
            self.assertEqual(data_repo['id'], 'test-repo')
            self.assertEqual(data_repo['display_name'], 'Test Repo')

            # Verify repo URLs
            host_urls = bind_data['host_urls']
            self.assertTrue(host_urls is not None)
            self.assertEqual(1, len(host_urls))
            self.assertEqual('https://localhost/pulp/repos/test-repo', host_urls[0])

            # Verify key URLs
            gpg_keys = bind_data['gpg_keys']
            self.assertTrue(gpg_keys is not None)
            self.assertEqual(0, len(gpg_keys))

        # Returned bind data
        verify_bind_data(returned_bind_data)

        # Verify
        #   Messaging bind data
        agent = Agent('test-consumer')
        repoproxy = agent.ConsumerXXX()
        calls = repoproxy.bind.history()
        lastbind = calls[-1]
        bindargs = lastbind[0]
        verify_bind_data(bindargs[1])

    def __bind_with_keys(self):
        '''
        Tests that binding to a repo with GPG keys returns a mapping of keys to contents.
        '''

        #
        # Test disabled until KeyStore is rewritten to not hardcode to /var/lib/pulp
        #

        # Setup
        #self.repo_api.create('test-repo', 'Test Repo', 'noarch')
        self.gc_repo_manager.create_repo('test-repo', 'Test Repo')
        #keyA = ('key-1', 'key-1-content')
        #keyB = ('key-2', 'key-2-content')
        #keylist = [keyA, keyB]
        #self.repo_api.addkeys('test-repo', keylist)

        self.consumer_api.create('test-consumer', None)

        # Test
        returned_bind_data = self.consumer_api.bind('test-consumer', 'test-repo')

        # Verify
        def verify_key_bind_data(bind_data):
            gpg_keys = bind_data['gpg_keys']
            self.assertTrue(gpg_keys is not None)

            self.assertEqual(2, len(gpg_keys))
            self.assertTrue('key-1' in gpg_keys)
            self.assertTrue('key-2' in gpg_keys)
            self.assertEqual('key-1-content', gpg_keys['key-1'])
            self.assertEqual('key-2-content', gpg_keys['key-2'])

        # Returned bind data
        verify_key_bind_data(returned_bind_data)

        # Verify
        #   Messaging bind data
        agent = Agent('test-consumer')
        repoproxy = agent.ConsumerXXX()
        calls = repoproxy.bind.history()
        lastbind = calls[-1]
        bindargs = lastbind[0]
        verify_bind_data(bindargs[1])

    def test_bind_invalid_consumer(self):
        '''
        Tests that an exception is properly thrown when the consumer doesn't exist.
        '''

        # Setup
        #self.repo_api.create('test-repo', 'Test Repo', 'noarch')
        self.gc_repo_manager.create_repo('test-repo', 'Test Repo')
        
        # Test
        self.assertRaises(PulpException, self.consumer_api.bind, 'fake-consumer', 'test-repo')

        # Verify
        #   Make sure no messages were sent over the bus
        agent = Agent('test-consumer')
        repoproxy = agent.ConsumerXXX()
        calls = repoproxy.bind.history()
        self.assertEqual(0, len(calls))

    def test_bind_invalid_repo(self):
        '''
        Tests that an exception is properly thrown when the repo doesn't exist.
        '''

        # Setup
        self.consumer_api.create('test-consumer', None)

        # Test
        self.assertRaises(PulpException, self.consumer_api.bind, 'test-consumer', 'fake-repo')

        # Verify
        #   Make sure no messages were sent over the bus
        agent = Agent('test-consumer')
        repoproxy = agent.ConsumerXXX()
        calls = repoproxy.bind.history()
        self.assertEqual(0, len(calls))

    def test_bind_with_cds(self):
        '''
        Tests the bind API when there are CDS instances associated with the bound repo.
        '''

        # Setup
        self.consumer_api.create('test-consumer', None)
        #self.repo_api.create('test-repo', 'Test Repo', 'noarch')
        self.gc_repo_manager.create_repo('test-repo', 'Test Repo')
        self.gc_distributor_manager.add_distributor('test-repo', 'mock-distributor', self.dist_config, True, distributor_id='my_dist')

        self.cds_api.register('cds1')
        self.cds_api.register('cds2')
        self.cds_api.associate_repo('cds1', 'test-repo')
        self.cds_api.associate_repo('cds2', 'test-repo')

        # Test
        bind_data = self.consumer_api.bind('test-consumer', 'test-repo')

        # Verify
        host_urls = bind_data['host_urls']
        self.assertEqual(3, len(host_urls)) # 2 CDS + Pulp server itself

        # The pulp server itself should be the last of the hosts
        self.assertTrue('localhost' in host_urls[2])


    # -- unbind test cases -------------------------------------------------------------------

    def test_unbind(self):
        '''
        Tests the happy path of unbinding a repo that is bound to the consumer.
        '''

        # Setup
        self.consumer_api.create('test-consumer', None, CAPABILITIES)
        #self.repo_api.create('test-repo', 'Test Repo', 'noarch')
        self.gc_repo_manager.create_repo('test-repo', 'Test Repo')
        self.gc_distributor_manager.add_distributor('test-repo', 'mock-distributor', self.dist_config, True, distributor_id='my_dist')

        self.consumer_api.bind('test-consumer', 'test-repo')

        consumer = self.consumer_api.consumer('test-consumer')
        self.assertTrue('test-repo' in consumer['repoids'])

        # Test
        self.consumer_api.unbind('test-consumer', 'test-repo')

        # Verify
        consumer = self.consumer_api.consumer('test-consumer')
        self.assertTrue('test-repo' not in consumer['repoids'])

        # Verify
        #   Messaging unbind data
        agent = Agent('test-consumer')
        repoproxy = agent.ConsumerXXX()
        calls = repoproxy.unbind.history()
        lastunbind = calls[-1]
        unbindargs = lastunbind[0]
        self.assertEqual(unbindargs[0], 'test-repo')

    def test_unbind_existing_repos(self):
        '''
        Tests that calling unbind when there are other repos bound does not affect
        those bindings.
        '''

        # Setup
        self.consumer_api.create('test-consumer', None, CAPABILITIES)
        #self.repo_api.create('test-repo-1', 'Test Repo', 'noarch')
        #self.repo_api.create('test-repo-2', 'Test Repo', 'noarch')
        self.gc_repo_manager.create_repo('test-repo-1', 'Test Repo')
        self.gc_repo_manager.create_repo('test-repo-2', 'Test Repo')

        self.gc_distributor_manager.add_distributor('test-repo-1', 'mock-distributor', self.dist_config, True, distributor_id='my_dist')
        self.gc_distributor_manager.add_distributor('test-repo-2', 'mock-distributor', self.dist_config, True, distributor_id='my_dist')
        
        self.consumer_api.bind('test-consumer', 'test-repo-1')
        self.consumer_api.bind('test-consumer', 'test-repo-2')

        consumer = self.consumer_api.consumer('test-consumer')
        self.assertTrue('test-repo-1' in consumer['repoids'])
        self.assertTrue('test-repo-2' in consumer['repoids'])

        # Test
        self.consumer_api.unbind('test-consumer', 'test-repo-1')

        # Verify
        consumer = self.consumer_api.consumer('test-consumer')
        self.assertTrue('test-repo-1' not in consumer['repoids'])
        self.assertTrue('test-repo-2' in consumer['repoids'])

        # Verify
        #   Messaging unbind data
        agent = Agent('test-consumer')
        repoproxy = agent.ConsumerXXX()
        calls = repoproxy.unbind.history()
        lastunbind = calls[-1]
        unbindargs = lastunbind[0]
        self.assertEqual(unbindargs[0], 'test-repo-1')

    def test_unbind_repo_not_bound(self):
        '''
        Tests that calling unbind on a repo that isn't bound acts as a no-op.
        '''

        # Setup
        self.consumer_api.create('test-consumer', None)
        #self.repo_api.create('test-repo', 'Test Repo', 'noarch')
        self.gc_repo_manager.create_repo('test-repo', 'Test Repo')

        # Test
        self.consumer_api.unbind('test-consumer', 'test-repo') # should not error

        # Verify
        #   Make sure no messages were sent over the bus
        agent = Agent('test-consumer')
        repoproxy = agent.ConsumerXXX()
        calls = repoproxy.unbind.history()
        self.assertEqual(0, len(calls))

    def test_unbind_invalid_consumer(self):
        '''
        Tests that calling unbind on a consumer that does not exist throws an error
        correctly.
        '''

        # Setup
        #self.repo_api.create('test-repo', 'Test Repo', 'noarch')
        self.gc_repo_manager.create_repo('test-repo', 'Test Repo')
        
        # Test
        self.assertRaises(PulpException, self.consumer_api.unbind, 'fake-consumer', 'test-repo')

        # Verify
        #   Make sure no messages were sent over the bus
        agent = Agent('fake-consumer')
        repoproxy = agent.ConsumerXXX()
        calls = repoproxy.unbind.history()
        self.assertEqual(0, len(calls))
        
    def test_package_install(self):
        '''
        Test package install
        '''
        # Setup
        id = 'test-consumer'
        packages = ['zsh',]
        self.consumer_api.create(id, None)
        
        # Test
        task = self.consumer_api.installpackages(id, packages)
        self.assertTrue(task is not None)
        task.run()
            
        # Verify
        agent = Agent(id)
        pkgproxy = agent.Packages()
        calls = pkgproxy.install.history()
        last = calls[-1]
        self.assertEqual(last.args[0], packages)
        
    def test_package_update(self):
        '''
        Test package update
        '''
        # Setup
        id = 'test-consumer'
        packages = ['zsh',]
        self.consumer_api.create(id, None)

        # Test
        task = self.consumer_api.updatepackages(id, packages)
        self.assertTrue(task is not None)
        task.run()

        # Verify
        agent = Agent(id)
        pkgproxy = agent.Packages()
        calls = pkgproxy.update.history()
        last = calls[-1]
        self.assertEqual(last.args[0], packages)

    def test_package_uninstall(self):
        '''
        Test package uninstall
        '''
        # Setup
        id = 'test-consumer'
        packages = ['zsh',]
        self.consumer_api.create(id, None)

        # Test
        task = self.consumer_api.uninstallpackages(id, packages)
        self.assertTrue(task is not None)
        task.run()

        # Verify
        agent = Agent(id)
        pkgproxy = agent.Packages()
        calls = pkgproxy.uninstall.history()
        last = calls[-1]
        self.assertEqual(last.args[0], packages)

    def test_pkgrp_install(self):
        '''
        Test package group install
        '''
        # Setup
        id = 'test-consumer'
        grpid = 'test-group'
        self.consumer_api.create(id, None)
        
        # Test
        task = self.consumer_api.installpackagegroups(id, [grpid])
        self.assertTrue(task is not None)
        task.run()
        
        # Verify
        agent = Agent(id)
        grpproxy = agent.PackageGroups()
        calls = grpproxy.install.history()
        last = calls[-1]
        self.assertEqual(last.args[0], [grpid])

    def test_pkgrp_uninstall(self):
        '''
        Test package group uninstall
        '''
        # Setup
        id = 'test-consumer'
        grpid = 'test-group'
        self.consumer_api.create(id, None)

        # Test
        task = self.consumer_api.uninstallpackagegroups(id, [grpid])
        self.assertTrue(task is not None)
        task.run()

        # Verify
        agent = Agent(id)
        grpproxy = agent.PackageGroups()
        calls = grpproxy.uninstall.history()
        last = calls[-1]
        self.assertEqual(last.args[0], [grpid])
