# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


import base
import random
import string

from pulp.server.auth import principal
from pulp.server.auth import authorization
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.auth.role.cud import super_user_role
from pulp.server.db.model.auth import User, Role
import pulp.server.exceptions as exceptions


# -- test cases ---------------------------------------------------------------

class RoleManagerTests(base.PulpServerTests):
    def setUp(self):
        super(RoleManagerTests, self).setUp()
        
        self.alpha_num = string.letters + string.digits

        self.user_manager = manager_factory.user_manager()
        self.user_query_manager = manager_factory.user_query_manager()
        self.role_manager = manager_factory.role_manager()
        self.role_query_manager = manager_factory.role_query_manager()
        self.permission_manager = manager_factory.permission_manager()
        self.permission_query_manager = manager_factory.permission_query_manager()
        
        self.role_manager.ensure_super_user_role()
        principal.clear_principal()

    def tearDown(self):
        super(RoleManagerTests, self).tearDown()

    def clean(self):
        base.PulpServerTests.clean(self)
        Role.get_collection().remove()

    # test data generation

    def _create_user(self):
        username = ''.join(random.sample(self.alpha_num, random.randint(6, 10)))
        password = ''.join(random.sample(self.alpha_num, random.randint(6, 10)))
        return self.user_manager.create_user(login=username, password=password, name=username)

    def _create_role(self):
        name = ''.join(random.sample(self.alpha_num, random.randint(6, 10)))
        return self.role_manager.create_role(name)

    def _create_resource(self):
        return '/%s/' % '/'.join(''.join(random.sample(self.alpha_num,
                                                       random.randint(6, 10)))
                                 for i in range(random.randint(2, 4)))
        
    # test role management

    def test_create_role(self):
        n = 'create_role'
        r1 = self.role_manager.create_role(n)
        r2 = self.role_query_manager.find_by_name(n)
        self.assertEquals(r1['_id'], r2['_id'])

    def test_delete_role(self):
        n = 'delete_role'
        r1 = self.role_manager.create_role(n)
        self.assertFalse(r1 is None)
        self.role_manager.delete_role(n)
        r2 = self.role_query_manager.find_by_name(n)
        self.assertTrue(r2 is None)

    def test_add_user(self):
        u = self._create_user()
        r = self._create_role()
        self.role_manager.add_user_to_role(r['name'], u['login'])
        user_names = [u['login'] for u in self.user_query_manager.get_users_belonging_to_role(r)]
        self.assertTrue(u['login'] in user_names)

    def test_remove_user(self):
        u = self._create_user()
        r = self._create_role()
        self.role_manager.add_user_to_role(r['name'], u['login'])
        self.role_manager.remove_user_from_role(r['name'], u['login'])
        user_names = [u['login'] for u in self.user_query_manager.get_users_belonging_to_role(r)]
        self.assertFalse(u['login'] in user_names)

    # test built in roles

    def test_super_users(self):
        role = self.role_query_manager.find_by_name(super_user_role)
        self.assertFalse(role is None)

    def test_super_users_grant(self):
        s = self._create_resource()
        n = authorization.operation_to_name(authorization.READ)
        self.role_manager.add_permissions_to_role(super_user_role, s, [n])
        #self.assertRaises(authorization.PulpAuthorizationError,
        #                  self.role_manager.add_permissions_to_role,
        #                  super_user_role, s, [n])

    def test_super_users_revoke(self):
        s = self._create_resource()
        n = authorization.operation_to_name(authorization.READ)
        self.role_manager.remove_permissions_from_role(super_user_role, s, [n])
#        self.assertRaises(authorization.PulpAuthorizationError,
#                          self.role_manager.remove_permissions_from_role,
#                          super_user_role, s, [n])

    def test_super_user_permissions(self):
        u = self._create_user()
        s = self._create_resource()
        r = super_user_role
        self.role_manager.add_user_to_role(r, u['login'])
        self.assertTrue(self.user_query_manager.is_authorized(s, u, authorization.CREATE))
        self.assertTrue(self.user_query_manager.is_authorized(s, u, authorization.READ))
        self.assertTrue(self.user_query_manager.is_authorized(s, u, authorization.UPDATE))
        self.assertTrue(self.user_query_manager.is_authorized(s, u, authorization.DELETE))
        self.assertTrue(self.user_query_manager.is_authorized(s, u, authorization.EXECUTE))
        
    # test multi-role/permission interaction

    def test_non_unique_permission_revoke(self):
        u = self._create_user()
        r1 = self._create_role()
        r2 = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        self.role_manager.add_user_to_role(r1['name'], u['login'])
        self.role_manager.add_user_to_role(r2['name'], u['login'])

        self.role_manager.add_permissions_to_role(r1['name'], s, [n])
        self.role_manager.add_permissions_to_role(r2['name'], s, [n])
        
        print self.role_query_manager.find_by_name(r1['name'])
        print "$$$$$$$$$$$$$$"
        print s, u, o
        print "$$$$$$$$$$$$$$"
        print self.permission_query_manager.find_by_resource(s)
        self.assertTrue(self.user_query_manager.is_authorized(s, u, o))
        self.role_manager.remove_permissions_from_role(r1['name'], s, [n])
        u = self.user_query_manager.find_by_login(u['login'])
        self.assertTrue(self.user_query_manager.is_authorized(s, u, o))

    def test_non_unique_permission_remove(self):
        u = self._create_user()
        r1 = self._create_role()
        r2 = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        self.role_manager.add_user_to_role(r1['name'], u['login'])
        self.role_manager.add_user_to_role(r2['name'], u['login'])
        self.role_manager.add_permissions_to_role(r1['name'], s, [n])
        self.role_manager.add_permissions_to_role(r2['name'], s, [n])
        self.assertTrue(self.user_query_manager.is_authorized(s, u, o))
        self.role_manager.remove_user_from_role(r1['name'], u['login'])
        self.assertTrue(self.user_query_manager.is_authorized(s, u, o))

    def test_non_unique_permission_delete(self):
        u = self._create_user()
        r1 = self._create_role()
        r2 = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        self.role_manager.add_user_to_role(r1['name'], u['login'])
        self.role_manager.add_user_to_role(r2['name'], u['login'])
        self.role_manager.add_permissions_to_role(r1['name'], s, [n])
        self.role_manager.add_permissions_to_role(r2['name'], s, [n])
        self.assertTrue(self.user_query_manager.is_authorized(s, u, o))
        self.role_manager.delete_role(r1['name'])
        self.assertTrue(self.user_query_manager.is_authorized(s, u, o))


