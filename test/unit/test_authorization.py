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

import logging
import os
import random
import string
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.auth import authorization, principal
from pulp.server.tasking.task import Task


class TestAuthorization(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        authorization.ensure_builtin_roles()
        principal.clear_principal()
        self.alhpa_num = string.letters + string.digits

    # test data generation

    def _create_user(self):
        username = ''.join(random.sample(self.alhpa_num, random.randint(6, 10)))
        password = ''.join(random.sample(self.alhpa_num, random.randint(6, 10)))
        return self.user_api.create(username, password, username, username)

    def _create_role(self):
        name = ''.join(random.sample(self.alhpa_num, random.randint(6, 10)))
        return self.role_api.create(name)

    def _create_resource(self):
        return '/%s/' % '/'.join(''.join(random.sample(self.alhpa_num,
                                                       random.randint(6, 10)))
                                 for i in range(random.randint(2, 4)))

    def _create_task(self):
        def _noop():
            pass
        return Task(_noop)

    # test individual user permissions

    def test_user_create_failure(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.CREATE
        self.assertFalse(authorization.is_authorized(r, u, o))

    def test_user_create_success(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.CREATE
        n = authorization.operation_to_name(o)
        authorization.grant_permission_to_user(r, u['login'], [n])
        self.assertTrue(authorization.is_authorized(r, u, o))

    def test_user_read_failure(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.READ
        self.assertFalse(authorization.is_authorized(r, u, o))

    def test_user_read_success(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.grant_permission_to_user(r, u['login'], [n])
        self.assertTrue(authorization.is_authorized(r, u, o))

    def test_user_update_failure(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.UPDATE
        self.assertFalse(authorization.is_authorized(r, u, o))

    def test_user_update_success(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.UPDATE
        n = authorization.operation_to_name(o)
        authorization.grant_permission_to_user(r, u['login'], [n])
        self.assertTrue(authorization.is_authorized(r, u, o))

    def test_user_delete_failure(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.DELETE
        self.assertFalse(authorization.is_authorized(r, u, o))

    def test_user_delete_success(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.DELETE
        n = authorization.operation_to_name(o)
        authorization.grant_permission_to_user(r, u['login'], [n])
        self.assertTrue(authorization.is_authorized(r, u, o))

    def test_user_execute_failure(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.EXECUTE
        self.assertFalse(authorization.is_authorized(r, u, o))

    def test_user_execute_success(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.EXECUTE
        n = authorization.operation_to_name(o)
        authorization.grant_permission_to_user(r, u['login'], [n])
        self.assertTrue(authorization.is_authorized(r, u, o))

    def test_user_permission_revoke(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.grant_permission_to_user(r, u['login'], [n])
        self.assertTrue(authorization.is_authorized(r, u, o))
        authorization.revoke_permission_from_user(r, u['login'], [n])
        self.assertFalse(authorization.is_authorized(r, u, o))

    def test_parent_permissions(self):
        u = self._create_user()
        r = self._create_resource()
        p = r.rsplit('/', 2)[0] + '/'
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.grant_permission_to_user(p, u['login'], [n])
        self.assertTrue(authorization.is_authorized(r, u, o))

    def test_root_permissions(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.grant_permission_to_user('/', u['login'], [n])
        self.assertTrue(authorization.is_authorized(r, u, o))

    # test role management

    def test_create_role(self):
        n = 'create_role'
        r1 = authorization.create_role(n)
        r2 = self.role_api.role(n)
        self.assertEquals(r1['_id'], r2['_id'])

    def test_delete_role(self):
        n = 'delete_role'
        r1 = self.role_api.create(n)
        self.assertFalse(r1 is None)
        authorization.delete_role(n)
        r2 = self.role_api.role(n)
        self.assertTrue(r2 is None)

    def test_add_user(self):
        u = self._create_user()
        r = self._create_role()
        authorization.add_user_to_role(r['name'], u['login'])
        user_names = [u['login'] for u in authorization.list_users_in_role(r['name'])]
        self.assertTrue(u['login'] in user_names)

    def test_remove_user(self):
        u = self._create_user()
        r = self._create_role()
        authorization.add_user_to_role(r['name'], u['login'])
        authorization.remove_user_from_role(r['name'], u['login'])
        user_names = [u['login'] for u in authorization.list_users_in_role(r['name'])]
        self.assertFalse(u['login'] in user_names)

    # test role permissions

    def test_role_create(self):
        u1 = self._create_user()
        u2 = self._create_user()
        r = self._create_role()
        s = self._create_resource()
        o = authorization.CREATE
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r['name'], u1['login'])
        authorization.grant_permission_to_role(s, r['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u1, o))
        self.assertFalse(authorization.is_authorized(s, u2, o))

    def test_role_read(self):
        u1 = self._create_user()
        u2 = self._create_user()
        r = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r['name'], u1['login'])
        authorization.grant_permission_to_role(s, r['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u1, o))
        self.assertFalse(authorization.is_authorized(s, u2, o))

    def test_role_update(self):
        u1 = self._create_user()
        u2 = self._create_user()
        r = self._create_role()
        s = self._create_resource()
        o = authorization.UPDATE
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r['name'], u1['login'])
        authorization.grant_permission_to_role(s, r['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u1, o))
        self.assertFalse(authorization.is_authorized(s, u2, o))

    def test_role_delete(self):
        u1 = self._create_user()
        u2 = self._create_user()
        r = self._create_role()
        s = self._create_resource()
        o = authorization.DELETE
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r['name'], u1['login'])
        authorization.grant_permission_to_role(s, r['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u1, o))
        self.assertFalse(authorization.is_authorized(s, u2, o))

    def test_role_execute(self):
        u1 = self._create_user()
        u2 = self._create_user()
        r = self._create_role()
        s = self._create_resource()
        o = authorization.EXECUTE
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r['name'], u1['login'])
        authorization.grant_permission_to_role(s, r['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u1, o))
        self.assertFalse(authorization.is_authorized(s, u2, o))

    def test_role_order_of_permission_grant(self):
        u1 = self._create_user()
        u2 = self._create_user()
        r1 = self._create_role()
        r2 = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        # add first, grant second
        authorization.add_user_to_role(r1['name'], u1['name'])
        authorization.grant_permission_to_role(s, r1['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u1, o))
        # grant first, add second
        authorization.grant_permission_to_role(s, r2['name'], [n])
        authorization.add_user_to_role(r2['name'], u2['name'])
        self.assertTrue(authorization.is_authorized(s, u2, o))

    def test_role_permission_revoke(self):
        u = self._create_user()
        r = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r['name'], u['login'])
        authorization.grant_permission_to_role(s, r['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u, o))
        authorization.revoke_permission_from_role(s, r['name'], [n])
        self.assertFalse(authorization.is_authorized(s, u, o))

    def test_role_permission_remove(self):
        u = self._create_user()
        r = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r['name'], u['login'])
        authorization.grant_permission_to_role(s, r['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u, o))
        authorization.remove_user_from_role(r['name'], u['login'])
        self.assertFalse(authorization.is_authorized(s, u, o))

    def test_role_permission_delete(self):
        u = self._create_user()
        r = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r['name'], u['login'])
        authorization.grant_permission_to_role(s, r['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u, o))
        authorization.delete_role(r['name'])
        self.assertFalse(authorization.is_authorized(s, u, o))

    # test multi-role/permission interaction

    def test_non_unique_permission_revoke(self):
        u = self._create_user()
        r1 = self._create_role()
        r2 = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r1['name'], u['login'])
        authorization.add_user_to_role(r2['name'], u['login'])
        authorization.grant_permission_to_role(s, r1['name'], [n])
        authorization.grant_permission_to_role(s, r2['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u, o))
        authorization.revoke_permission_from_role(s, r1['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u, o))

    def test_non_unique_permission_remove(self):
        u = self._create_user()
        r1 = self._create_role()
        r2 = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r1['name'], u['login'])
        authorization.add_user_to_role(r2['name'], u['login'])
        authorization.grant_permission_to_role(s, r1['name'], [n])
        authorization.grant_permission_to_role(s, r2['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u, o))
        authorization.remove_user_from_role(r1['name'], u['login'])
        self.assertTrue(authorization.is_authorized(s, u, o))

    def test_non_unique_permission_delete(self):
        u = self._create_user()
        r1 = self._create_role()
        r2 = self._create_role()
        s = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        authorization.add_user_to_role(r1['name'], u['login'])
        authorization.add_user_to_role(r2['name'], u['login'])
        authorization.grant_permission_to_role(s, r1['name'], [n])
        authorization.grant_permission_to_role(s, r2['name'], [n])
        self.assertTrue(authorization.is_authorized(s, u, o))
        authorization.delete_role(r1['name'])
        self.assertTrue(authorization.is_authorized(s, u, o))

    # test built in roles

    def test_super_users(self):
        role = self.role_api.role(authorization.super_user_role)
        self.assertFalse(role is None)

    def test_super_users_grant(self):
        s = self._create_resource()
        n = authorization.operation_to_name(authorization.READ)
        self.assertRaises(authorization.PulpAuthorizationError,
                          authorization.grant_permission_to_role,
                          s, authorization.super_user_role, [n])

    def test_super_users_revoke(self):
        s = self._create_resource()
        n = authorization.operation_to_name(authorization.READ)
        self.assertRaises(authorization.PulpAuthorizationError,
                          authorization.revoke_permission_from_role,
                          s, authorization.super_user_role, [n])

    def test_super_users_remove(self):
        u = self._create_user()
        authorization.add_user_to_role(authorization.super_user_role, u['name'])
        self.assertRaises(authorization.PulpAuthorizationError,
                          authorization.remove_user_from_role,
                          authorization.super_user_role, u['name'])

    def test_super_user_permissions(self):
        u = self._create_user()
        s = self._create_resource()
        r = authorization.super_user_role
        authorization.add_user_to_role(r, u['name'])
        self.assertTrue(authorization.is_authorized(s, u, authorization.CREATE))
        self.assertTrue(authorization.is_authorized(s, u, authorization.READ))
        self.assertTrue(authorization.is_authorized(s, u, authorization.UPDATE))
        self.assertTrue(authorization.is_authorized(s, u, authorization.DELETE))
        self.assertTrue(authorization.is_authorized(s, u, authorization.EXECUTE))

    # test consumer auto-permissions

    def test_consumer_users(self):
        role = self.role_api.role(authorization.consumer_users_role)
        self.assertFalse(role is None)

    def test_consumer_users_grant(self):
        s = self._create_resource()
        n = authorization.operation_to_name(authorization.READ)
        self.assertRaises(authorization.PulpAuthorizationError,
                          authorization.grant_permission_to_role,
                          s, authorization.consumer_users_role, [n])

    def test_consumer_users_revoke(self):
        s = self._create_resource()
        n = authorization.operation_to_name(authorization.READ)
        self.assertRaises(authorization.PulpAuthorizationError,
                          authorization.revoke_permission_from_role,
                          s, authorization.consumer_users_role, [n])

    def test_consumer_user_permissions(self):
        u = self._create_user()
        s = '/consumers/'
        r = authorization.consumer_users_role
        authorization.add_user_to_role(r, u['name'])
        self.assertTrue(authorization.is_authorized(s, u, authorization.CREATE))
        self.assertTrue(authorization.is_authorized(s, u, authorization.READ))
        self.assertFalse(authorization.is_authorized(s, u, authorization.UPDATE))
        self.assertFalse(authorization.is_authorized(s, u, authorization.DELETE))
        self.assertFalse(authorization.is_authorized(s, u, authorization.EXECUTE))

    # test task auto-permissions

    def test_task_permissions(self):
        u = self._create_user()
        t = self._create_task()
        r = '/tasks/%s/' % t.id
        principal.set_principal(u)
        grant = authorization.GrantPermissionsForTask()
        grant(t)
        self.assertTrue(authorization.is_authorized(r, u, authorization.READ))
        self.assertTrue(authorization.is_authorized(r, u, authorization.DELETE))
        revoke = authorization.RevokePermissionsForTask()
        revoke(t)
        self.assertFalse(authorization.is_authorized(r, u, authorization.READ))
        self.assertFalse(authorization.is_authorized(r, u, authorization.DELETE))


if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
