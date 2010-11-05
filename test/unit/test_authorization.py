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
import base64
import logging
import os
import sys
import unittest
import web

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)


from pulp.server.api.user import UserApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.role import PermissionApi
from pulp.server.api.role import RoleApi
from pulp.server.db.model import RoleActionType
from pulp.server.db.model import RoleResourceType


import pulp.server.auth.auth as auth
import testutil

class TestAuthorization(unittest.TestCase):

    def setUp(self):
        self.config = testutil.load_test_config()
        self.uapi = UserApi()
        self.capi = ConsumerApi()
        self.roleapi = RoleApi()
        self.repoapi = RepoApi()
        self.userapi = UserApi()
        self.permapi = PermissionApi()
        # Make sure to reset the principal between tests
        auth.set_principal(auth.SystemPrincipal())

    def tearDown(self):
        self.uapi.clean()
        self.capi.clean()
        self.roleapi.clean()
        self.repoapi.clean()
        self.permapi.clean()
        testutil.common_cleanup()

    def test_create_role(self):
        # Create 2 roles so you check for proper unique ids
        role = self.create_role('test-role')
        role2 = self.create_role('test-role2')
        self.assertTrue(role['name'])
        self.assertTrue(role['description'])
        self.assertTrue(role['action_types'])
        self.assertTrue(role['resource_type'])

    def test_edit_role(self):
        role = self.create_role('edit-role')
        role['description'] = 'updated desc'
        self.roleapi.update(role)
        updated = self.roleapi.role('edit-role')
        self.assertEquals(updated['description'], 'updated desc')
    
    def test_delete_role(self):
        role = self.create_role('delete-role')
        self.assertTrue(self.roleapi.role('delete-role'))
        self.roleapi.delete(role['name'])
        r = self.roleapi.role('delete-role')
        self.assertFalse(self.roleapi.role('delete-role'))
        
    def test_role_within_role(self):
        role1 = self.create_role('root-role')
        role2 = self.create_role('child-role')
        role2['parent'] = role1
        self.roleapi.update(role2)
        
        updated_root = self.roleapi.role('root-role')
        
        updated_child = self.roleapi.role('child-role')
        self.assertEquals(updated_child['parent'], updated_root)
        
        
    def test_create_permission(self):
        role = self.create_role('perm-test-role')
        repo = self.repoapi.create('perm-test-repo', 'perm-test', 'i386')
        user = self.userapi.create('perm-test-user')
        perm = self.permapi.create(role, repo, user)  
        self.assertTrue(perm)
        self.assertTrue(perm['role'])
        self.assertTrue(perm['instance'])
        self.assertTrue(perm['user'])
        
    # Util Method
    def create_role(self, name):
        desc = 'test desc for role'
        action_type = [RoleActionType.CREATE, RoleActionType.WRITE]
        resource_type = RoleResourceType.REPO
        
        role = self.roleapi.create(name, desc, action_type, resource_type)
        return role
    


        
if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
