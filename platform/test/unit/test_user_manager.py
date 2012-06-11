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

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.auth import principal
import pulp.server.auth.cert_generator as cert_generator
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server.auth.certificate import Certificate
from pulp.server.managers.user import UserManager

# -- constants ----------------------------------------------------------------



# -- test cases ---------------------------------------------------------------

class UserManagerTests(testutil.PulpTest):
    def setUp(self):
        testutil.PulpTest.setUp(self)

        self.config = testutil.load_test_config()

        # Hardcoded to /var/lib/pulp, so change here to avoid permissions issues
        self.default_sn_path = SerialNumber.PATH
        SerialNumber.PATH = '/tmp/sn.dat'
        sn = SerialNumber()
        sn.reset()

        self.manager = UserManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)

        SerialNumber.PATH = self.default_sn_path

    def test_generate_user_certificate(self):

        # Setup

        # TODO: Fix this when UserManager can create users
        admin_user = self.user_api.create('test-admin')
        principal.set_principal(admin_user) # pretend the user is logged in

        # Test
        cert = self.manager.generate_user_certificate()

        # Verify
        self.assertTrue(cert is not None)

        certificate = Certificate(content=cert)
        cn = certificate.subject()['CN']
        username, id = cert_generator.decode_admin_user(cn)

        self.assertEqual(username, admin_user.login)
        self.assertEqual(id, admin_user.id)

