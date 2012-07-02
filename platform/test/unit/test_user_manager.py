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

from pulp.server.auth import principal
import pulp.server.auth.cert_generator as cert_generator
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server.auth.certificate import Certificate
from pulp.server.managers.auth.user import UserManager

from pulp.server.db.model.auth import User
import pulp.server.exceptions as exceptions


# -- test cases ---------------------------------------------------------------

class UserManagerTests(base.PulpServerTests):
    def setUp(self):
        super(UserManagerTests, self).setUp()

        # Hardcoded to /var/lib/pulp, so change here to avoid permissions issues
        self.default_sn_path = SerialNumber.PATH
        SerialNumber.PATH = '/tmp/sn.dat'
        sn = SerialNumber()
        sn.reset()

        self.manager = UserManager()

    def tearDown(self):
        super(UserManagerTests, self).tearDown()

        SerialNumber.PATH = self.default_sn_path

    def clean(self):
        base.PulpServerTests.clean(self)

        User.get_collection().remove()

    def test_generate_user_certificate(self):

        # Setup
        user_manager = UserManager()

        # TODO: Fix this when UserManager can create users
        admin_user = user_manager.create_user('test-admin')
        principal.set_principal(admin_user) # pretend the user is logged in

        # Test
        cert = self.manager.generate_user_certificate()

        # Verify
        self.assertTrue(cert is not None)

        certificate = Certificate(content=cert)
        cn = certificate.subject()['CN']
        username, id = cert_generator.decode_admin_user(cn)

        self.assertEqual(username, admin_user['login'])
        self.assertEqual(id, admin_user['id'])

    def test_create(self):
        # Setup
        login = 'login-test'
        clear_txt_pass = 'some password'

        # Test
        user = self.manager.create_user(login, clear_txt_pass,
                                                name = "King of the World",
                                                roles = ['test-role'])

        # Verify
        self.assertTrue(user is not None)
        user = self.manager.find_by_login(login)
        self.assertTrue(user is not None)
        self.assertNotEqual(clear_txt_pass, user['password'])

    def test_duplicate(self):
        # Setup
        login = 'dupe-test'
        clear_txt_pass = 'some password'
        user = self.manager.create_user(login, clear_txt_pass)

        # Test and verify
        try:
            user = self.manager.create_user(login, clear_txt_pass)
            self.fail('User with an existing login did not raise an exception')
        except exceptions.DuplicateResource, e:
            self.assertTrue(login in e)
            print(e) # for coverage


    def test_user_list(self):
        # Setup
        login = 'login-test'
        password = 'some password'
        user = self.manager.create_user(login, password)

        # Test
        users = self.manager.find_all()

        # Verify
        assert(len(users) == 1)


    def test_delete(self):
        # Setup
        login = 'login-test'
        password = 'some password'
        user = self.manager.create_user(login, password)

        # test
        self.manager.delete_user(login)

        # Verify
        user = self.manager.find_by_login(login)
        assert(user is None)

    def test_update_password(self):
        # Setup
        login = 'login-test'
        password = 'some password'
        user = self.manager.create_user(login, password)

        # Test
        changed_password = 'some other password'
        d = dict(password=changed_password)
        user = self.manager.update_user(login, delta=d)

        # Verify
        user = self.manager.find_by_login(login)
        self.assertTrue(user is not None)
        self.assertTrue(user['password'] is not None)
        self.assertNotEqual(changed_password, user['password'])

