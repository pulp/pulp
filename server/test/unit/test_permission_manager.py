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

from pulp.server.auth import authorization
from pulp.server.managers import factory as manager_factory
import pulp.server.exceptions as exceptions

from pulp.server.db.model.auth import Role

# -- test cases ---------------------------------------------------------------


class PermissionManagerTests(base.PulpServerTests):
    def setUp(self):
        super(PermissionManagerTests, self).setUp()

        self.alpha_num = string.letters + string.digits

        self.user_manager = manager_factory.user_manager()
        self.user_query_manager = manager_factory.user_query_manager()
        self.role_manager = manager_factory.role_manager()
        self.role_query_manager = manager_factory.role_query_manager()
        self.permission_manager = manager_factory.permission_manager()
        self.permission_query_manager = manager_factory.permission_query_manager()

        self.role_manager.ensure_super_user_role()
        manager_factory.principal_manager().clear_principal()

    def tearDown(self):
        super(PermissionManagerTests, self).tearDown()

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
        self.permission_manager.grant(r, u['login'], [o])
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
        self.permission_manager.grant(r, u['login'], [o])
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
        self.permission_manager.grant(r, u['login'], [o])
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
        self.permission_manager.grant(r, u['login'], [o])
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
        self.permission_manager.grant(r, u['login'], [o])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_user_permission_revoke(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.READ
        self.permission_manager.grant(r, u['login'], [o])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))
        self.permission_manager.revoke(r, u['login'], [o])
        self.assertFalse(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_non_existing_user_permission_revoke(self):
        login = 'non-existing-user-login'
        r = self._create_resource()
        o = authorization.READ
        try:
            self.permission_manager.revoke(r, login, [o])
            self.fail('Non-existing user permission revoke did not raise an exception')
        except exceptions.MissingResource, e:
            self.assertTrue(login in str(e))

    def test_parent_permissions(self):
        u = self._create_user()
        r = self._create_resource()
        p = r.rsplit('/', 2)[0] + '/'
        o = authorization.READ
        self.permission_manager.grant(p, u['login'], [o])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_root_permissions(self):
        u = self._create_user()
        r = self._create_resource()
        o = authorization.READ
        self.permission_manager.grant('/', u['login'], [o])
        self.assertTrue(self.user_query_manager.is_authorized(r, u['login'], o))

    def test_operation_name_to_value(self):
        pm = manager_factory.permission_manager()
        self.assertEqual(pm.operation_name_to_value('CREATE'), authorization.CREATE)
        self.assertEqual(pm.operation_name_to_value('READ'), authorization.READ)
        self.assertEqual(pm.operation_name_to_value('UPDATE'), authorization.UPDATE)
        self.assertEqual(pm.operation_name_to_value('DELETE'), authorization.DELETE)
        self.assertEqual(pm.operation_name_to_value('EXECUTE'), authorization.EXECUTE)
        self.assertRaises(exceptions.InvalidValue, pm.operation_name_to_value, 'random')
        self.assertRaises(exceptions.InvalidValue, pm.operation_name_to_value, None)
        self.assertRaises(exceptions.InvalidValue, pm.operation_name_to_value, '')

    def test_operation_names_to_values(self):
        pm = manager_factory.permission_manager()
        test1 = ['CREATE', 'delete']
        test1_values = [authorization.CREATE, authorization.DELETE]
        test2 = ['execute']
        test2_values = [authorization.EXECUTE]
        test3 = []
        test3_values = []
        test4 = ['READ', 'UPDATE', 'random']
        test5 = None
        self.assertEqual(pm.operation_names_to_values(test1), test1_values)
        self.assertEqual(pm.operation_names_to_values(test2), test2_values)
        self.assertEqual(pm.operation_names_to_values(test3), test3_values)
        self.assertRaises(exceptions.InvalidValue, pm.operation_names_to_values, test4)
        self.assertRaises(exceptions.InvalidValue, pm.operation_names_to_values, test5)

    def test_operation_value_to_name(self):
        pm = manager_factory.permission_manager()
        self.assertEqual(pm.operation_value_to_name(authorization.CREATE), 'CREATE')
        self.assertEqual(pm.operation_value_to_name(authorization.READ), 'READ')
        self.assertEqual(pm.operation_value_to_name(authorization.UPDATE), 'UPDATE')
        self.assertEqual(pm.operation_value_to_name(authorization.DELETE), 'DELETE')
        self.assertEqual(pm.operation_value_to_name(authorization.EXECUTE), 'EXECUTE')
        self.assertEqual(pm.operation_value_to_name('RANDOM'), None)
        self.assertEqual(pm.operation_value_to_name(99), None)
        self.assertEqual(pm.operation_value_to_name(-2), None)
