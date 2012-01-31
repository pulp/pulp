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
import logging
import sys
import os
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_group import ConsumerGroupApi

class TestUsers(testutil.PulpAsyncTest):
    
    def test_consumer_create_with_keyvalues(self):
        cid = 'client1'
        test_keyvalues = {"foo.bar":"bar.foo", "a.b":"b.a"}
        c = self.consumer_api.create(cid, None, key_value_pairs=test_keyvalues)
        self.assertTrue(c is not None)
        
    def test_consumer_add_keyvalue(self):
        cid = 'client1'
        c = self.consumer_api.create(cid, 'some consumer desc')
        self.assertTrue(c is not None)
        self.assertTrue(c['id'] == cid)  
        
        key_values = self.consumer_api.get_keyvalues(cid)
        self.assertTrue(key_values == {})
        
        self.consumer_api.add_key_value_pair(cid, 'test-key1', 'value1')
        key_values = self.consumer_api.get_keyvalues(cid)
        self.assertTrue(key_values['test-key1'] == 'value1')

    def test_consumer_update_keyvalue(self):
        cid = 'client1'
        c = self.consumer_api.create(cid, 'some consumer desc')
        self.consumer_api.add_key_value_pair(cid, 'test-key1', 'value1')

        self.consumer_api.update_key_value_pair(cid, 'test-key1', 'value1-updated')
        key_values = self.consumer_api.get_keyvalues(cid)
        self.assertTrue(key_values['test-key1'] == 'value1-updated')
        
    def test_consumer_delete_keyvalue(self):       
        cid = 'client1'   
        c = self.consumer_api.create(cid, 'some consumer desc')
        self.consumer_api.add_key_value_pair(cid, 'test-key1', 'value1')

        self.consumer_api.delete_key_value_pair(cid, 'test-key1')
        key_values = self.consumer_api.get_keyvalues(cid)
        self.assertTrue(key_values == {})

    def test_consumergroup_add_keyvalue(self):
        cgid = 'test-group'
        cg = self.consumer_group_api.create(cgid, 'test group')
        self.assertTrue(cg is not None)
        self.assertTrue(cg['id'] == cgid)

        self.consumer_group_api.add_key_value_pair(cgid, 'test-key1', 'value1', 'false')
        cg = self.consumer_group_api.consumergroup(cgid)
        key_values = cg['key_value_pairs']
        self.assertTrue(key_values['test-key1'] == 'value1')

    def test_consumergroup_update_keyvalue(self):
        cgid = 'test-group'
        cg = self.consumer_group_api.create(cgid, 'test group')
        self.consumer_group_api.add_key_value_pair(cgid, 'test-key1', 'value1', 'true')
        self.consumer_group_api.update_key_value_pair(cgid, 'test-key1', 'value2')
        cg = self.consumer_group_api.consumergroup(cgid)
        key_values = cg['key_value_pairs']
        self.assertTrue(key_values['test-key1'] == 'value2')
       
    def test_consumergroup_delete_keyvalue(self):
        cgid = 'test-group'
        cg = self.consumer_group_api.create(cgid, 'test group')
                
        self.consumer_group_api.add_key_value_pair(cgid, 'test-key1', 'value1', 'true')
        self.consumer_group_api.delete_key_value_pair(cgid, 'test-key1')
        cg = self.consumer_group_api.consumergroup(cgid)
        key_values = cg['key_value_pairs']
        self.assertTrue(key_values == {})

if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
