#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
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

# Python
import sys
import os
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import mocks
import testutil
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_group import ConsumerGroupApi
from pulp.server.api.repo import RepoApi
from pulp.server.pexceptions import PulpException


# -- test cases ---------------------------------------------------------------------------

class TestConsumerApi(unittest.TestCase):

    def clean(self):
        self.capi.clean()
        self.cgapi.clean()   
        self.rapi.clean()
        
    def setUp(self):
        mocks.install()
        self.config = testutil.load_test_config()
        self.capi = ConsumerApi()
        self.cgapi = ConsumerGroupApi()
        self.rapi = RepoApi()
        self.clean()

    def tearDown(self):
        self.clean()
        testutil.common_cleanup()
        
    def test_create_consumergroup(self):
        cg = self.cgapi.create('some-id', 'some description')
        found = self.cgapi.consumergroup('some-id')
        assert(found is not None)
        assert(found['description'] == 'some description')
        assert(found['id'] == 'some-id')

        found = self.cgapi.consumergroup('some-id-that-doesnt-exist')
        assert(found is None)
        
        # try creating another consumer group with same id
        try:
            cg = self.cgapi.create('some-id', 'some description')
            assert(False)
        except PulpException:
            pass
        
    def test_create_consumergroup_with_consumerids(self):
        try:
            cg = self.cgapi.create('some-id', 'some description', consumerids=['con-test1','con-test2'])
            assert(False)
        except PulpException:
            pass    
        
        self.capi.create('con-test1', 'con-test1')
        self.capi.create('con-test2', 'con-test2')
        cg = self.cgapi.create('some-id', 'some description', consumerids=['con-test1','con-test2'])
        assert('con-test1' in cg['consumerids'])
        assert('con-test2' in cg['consumerids'])
        
    def test_consumergroup_update(self):
        cgs = self.cgapi.consumergroups()
        assert(len(cgs) == 0)
        
        try:
            self.cgapi.update('some-id', {'description':'some other description'})
            assert(False)
        except:
            pass
        
        self.cgapi.create('some-id', 'some description')
        self.cgapi.update('some-id', {'description':'some other description'})
        cgs = self.cgapi.consumergroups()
        assert(len(cgs) == 1)
        
        try:
            self.cgapi.update('some-id', {'foo':'bar'})
            assert(False)
        except:
            pass
        
    
    def test_add_consumer(self):
        try:
            self.cgapi.add_consumer('groupid', 'consumerid')
            assert(False)
        except:
            pass
        
        self.cgapi.create('groupid', 'some description')
        try:
            self.cgapi.add_consumer('groupid', 'consumerid')
            assert(False)
        except:
            pass
        self.capi.create('consumerid', 'consumerid')
        self.cgapi.add_consumer('groupid', 'consumerid')
        # try adding it again 
        self.cgapi.add_consumer('groupid', 'consumerid')
        
        assert('consumerid' in self.cgapi.consumers('groupid'))
        
        
    def test_delete_consumer(self):
        try:
            self.cgapi.delete_consumer('groupid', 'consumerid')
            assert(False)
        except:
            pass
        
        self.capi.create('consumerid', 'consumerid')
        self.cgapi.create('groupid', 'some description', ['consumerid'])
        self.cgapi.delete_consumer('groupid', 'consumerid')
        # deleting again should not result in error
        self.cgapi.delete_consumer('groupid', 'consumerid')
        assert('consumerid' not in self.cgapi.consumers('groupid'))
        
    def test_bind_repo(self):
        try:
            self.cgapi.bind('groupid', 'test-repo')
            assert(False)
        except:
            pass
        
        self.capi.create('consumerid1', 'consumerid1')
        self.capi.create('consumerid2', 'consumerid2')
        self.cgapi.create('groupid', 'some description', ['consumerid1', 'consumerid2'])
        
        try:
            self.cgapi.bind('groupid', 'test-repo')
            assert(False)
        except:
            pass
        
        self.rapi.create(id='test-repo', name='test-repo', arch='i386')
        
        self.cgapi.bind('groupid', 'test-repo')
        c1 = self.capi.consumer('consumerid1')
        c2 = self.capi.consumer('consumerid2')
        assert('test-repo' in c1['repoids'])
        assert('test-repo' in c2['repoids'])
        
    def test_unbind_repo(self):
        try:
            self.cgapi.unbind('groupid', 'test-repo')
            assert(False)
        except:
            pass
        
        self.capi.create('consumerid1', 'consumerid1')
        self.capi.create('consumerid2', 'consumerid2')
        self.cgapi.create('groupid', 'some description', ['consumerid1', 'consumerid2'])
        
        try:
            self.cgapi.unbind('groupid', 'test-repo')
            assert(False)
        except:
            pass
        
        self.rapi.create(id='test-repo', name='test-repo', arch='i386')
        
        self.cgapi.bind('groupid', 'test-repo')
        self.cgapi.unbind('groupid', 'test-repo')
        c1 = self.capi.consumer('consumerid1')
        c2 = self.capi.consumer('consumerid2')
        assert('test-repo' not in c1['repoids'])
        assert('test-repo' not in c2['repoids'])
        
    def test_add_consumer_with_conflicting_key_value(self):
        self.capi.create('consumerid', 'consumerid')
        self.capi.add_key_value_pair('consumerid', 'key1', 'value1')
        
        self.cgapi.create('groupid', 'some description')
        self.cgapi.add_key_value_pair('groupid', 'key1', 'value2')
        
        try:
            self.cgapi.add_consumer('groupid', 'consumerid')
            assert(False)
        except:
            pass

        self.capi.delete_key_value_pair('consumerid', 'key1')
        self.cgapi.add_consumer('groupid', 'consumerid')

        