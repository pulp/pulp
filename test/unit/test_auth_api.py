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
import os
import sys
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.server.api.auth import AuthApi
from pulp.server.api.user import UserApi
import pulp.server.auth.auth as principal
import pulp.server.auth.cert_generator as cert_generator
from pulp.server.auth.certificate import Certificate
import testutil


class TestAuthApi(unittest.TestCase):

    def clean(self):
        self.user_api.clean()
        testutil.common_cleanup()

    def setUp(self):
        self.config = testutil.load_test_config()
        self.auth_api = AuthApi()
        self.user_api = UserApi()
        self.clean()

    def tearDown(self):
        self.clean()

    def test_admin_certificate(self):
        # Setup
        admin_user = self.user_api.create('test-admin')
        principal.set_principal(admin_user) # pretend the user is logged in

        # Test
        private_key, cert = self.auth_api.admin_certificate()

        # Verify
        self.assertTrue(private_key is not None)
        self.assertTrue(cert is not None)

        certificate = Certificate(content=cert)
        cn = certificate.subject()['CN']
        username, id = cert_generator.decode_admin_user(cn)

        self.assertEqual(username, admin_user.login)
        self.assertEqual(id, admin_user.id)
