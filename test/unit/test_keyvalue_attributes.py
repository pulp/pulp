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

# Python
import logging
import sys
import os
import time
import unittest
import uuid

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import mocks
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_group import ConsumerGroupApi
import testutil


class TestUsers(unittest.TestCase):

    def clean(self):
        self.capi.clean()
        self.cgapi.clean()   

    def setUp(self):
        mocks.install()
        self.config = testutil.load_test_config()
        self.capi = ConsumerApi()
        self.cgapi = ConsumerGroupApi()
        self.clean()

    def tearDown(self):
        self.clean()
        testutil.common_cleanup()

    def test_consumer_add_keyvalue(self):
        cid = 'client1'
        c = self.capi.create(cid, 'some consumer desc')
        self.assertTrue(c is not None)
        self.assertTrue(c['id'] == cid)  
        
        key_values = self.capi.get_keyvalues(cid)
        self.assertTrue(key_values == {})
        
        self.capi.add_key_value_pair(cid, 'test-key1', 'value1')
        key_values = self.capi.get_keyvalues(cid)
        self.assertTrue(key_values['test-key1'] == 'value1')

    def test_consumer_update_keyvalue(self):
        cid = 'client1'
        c = self.capi.create(cid, 'some consumer desc')
        self.capi.add_key_value_pair(cid, 'test-key1', 'value1')

        self.capi.update_key_value_pair(cid, 'test-key1', 'value1-updated')
        key_values = self.capi.get_keyvalues(cid)
        self.assertTrue(key_values['test-key1'] == 'value1-updated')
        
    def test_consumer_delete_keyvalue(self):       
        cid = 'client1'   
        c = self.capi.create(cid, 'some consumer desc')
        self.capi.add_key_value_pair(cid, 'test-key1', 'value1')

        self.capi.delete_key_value_pair(cid, 'test-key1')
        key_values = self.capi.get_keyvalues(cid)
        self.assertTrue(key_values == {})

    def test_consumergroup_add_keyvalue(self):
        cgid = 'test-group'
        cg = self.cgapi.create(cgid, 'test group')
        self.assertTrue(cg is not None)
        self.assertTrue(cg['id'] == cgid)

        self.cgapi.add_key_value_pair(cgid, 'test-key1', 'value1', 'false')
        cg = self.cgapi.consumergroup(cgid)
        key_values = cg['key_value_pairs']
        self.assertTrue(key_values['test-key1'] == 'value1')

    def test_consumergroup_update_keyvalue(self):
        cgid = 'test-group'
        cg = self.cgapi.create(cgid, 'test group')
        self.cgapi.add_key_value_pair(cgid, 'test-key1', 'value1', 'true')
        self.cgapi.update_key_value_pair(cgid, 'test-key1', 'value2')
        cg = self.cgapi.consumergroup(cgid)
        key_values = cg['key_value_pairs']
        self.assertTrue(key_values['test-key1'] == 'value2')
       
    def test_consumergroup_delete_keyvalue(self):
        cgid = 'test-group'
        cg = self.cgapi.create(cgid, 'test group')
                
        self.cgapi.add_key_value_pair(cgid, 'test-key1', 'value1', 'true')
        self.cgapi.delete_key_value_pair(cgid, 'test-key1')
        cg = self.cgapi.consumergroup(cgid)
        key_values = cg['key_value_pairs']
        self.assertTrue(key_values == {})

if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
