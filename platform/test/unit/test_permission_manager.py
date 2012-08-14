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
        
        
    def test_user_create_failure(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.CREATE
        self.assertFalse(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_create_success(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.CREATE
        n = authorization.operation_to_name(o)
        self.permission_manager.grant(r, u['login'], [n])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_read_failure(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.READ
        self.assertFalse(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_read_success(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        self.permission_manager.grant(r, u['login'], [n])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_update_failure(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.UPDATE
        self.assertFalse(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_update_success(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.UPDATE
        n = authorization.operation_to_name(o)
        self.permission_manager.grant(r, u['login'], [n])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_delete_failure(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.DELETE
        self.assertFalse(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_delete_success(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.DELETE
        n = authorization.operation_to_name(o)
        self.permission_manager.grant(r, u['login'], [n])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_execute_failure(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.EXECUTE
        self.assertFalse(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_execute_success(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.EXECUTE
        n = authorization.operation_to_name(o)
        self.permission_manager.grant(r, u['login'], [n])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_permission_revoke(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        self.permission_manager.grant(r, u['login'], [n])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))
        self.permission_manager.revoke(r, u['login'], [n])
        self.assertFalse(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_parent_permissions(self):
        u = self._create_user()
        r = self._create_resource()
        p = r.rsplit('/', 2)[0] + '/'
        o = authorization.READ
        n = authorization.operation_to_name(o)
        self.permission_manager.grant(p, u['login'], [n])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_root_permissions(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.READ
        n = authorization.operation_to_name(o)
        self.permission_manager.grant('/', u['login'], [n])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))
        


