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

class UserCertificateControllerTests(testutil.PulpV2WebserviceTest):

    def setUp(self):
        testutil.PulpV2WebserviceTest.setUp(self)

        self.config = testutil.load_test_config()

        # Hardcoded to /var/lib/pulp, so change here to avoid permissions issues
        self.default_sn_path = SerialNumber.PATH
        SerialNumber.PATH = '/tmp/sn.dat'
        sn = SerialNumber()
        sn.reset()

    def tearDown(self):
        testutil.PulpV2WebserviceTest.tearDown(self)

        SerialNumber.PATH = self.default_sn_path

    def test_get(self):
        # Setup

        # TODO: Fix this when UserManager lookup
        user = self.user_api.user('ws-user')

        # Test
        status, body = self.post('/v2/actions/login/')

        # Verify
        self.assertEqual(200, status)

        certificate = Certificate(content=str(body))
        cn = certificate.subject()['CN']
        username, id = cert_generator.decode_admin_user(cn)

        self.assertEqual(username, user['login'])
        self.assertEqual(id, user['id'])
