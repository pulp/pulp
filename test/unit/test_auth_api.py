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
import os
import shutil
import sys
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.server.api.auth import AuthApi
from pulp.server.api.user import UserApi
from pulp.server.auth import principal
import pulp.server.auth.cert_generator as cert_generator
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server.auth.certificate import Certificate

import testutil

SerialNumber.PATH = '/tmp/sn.dat'


CERT_DIR = '/tmp/test_repo_cert_utils/repos'
GLOBAL_CERT_DIR = '/tmp/test_repo_cert_utils/global'


class TestAuthApi(unittest.TestCase):

    def clean(self):
        if os.path.exists(CERT_DIR):
            shutil.rmtree(CERT_DIR)
        if os.path.exists(GLOBAL_CERT_DIR):
            shutil.rmtree(GLOBAL_CERT_DIR)
        self.user_api.clean()
        testutil.common_cleanup()

    def setUp(self):
        self.config = testutil.load_test_config()
        self.config.set('repos', 'cert_location', CERT_DIR)
        self.config.set('repos', 'global_cert_location', GLOBAL_CERT_DIR)
        self.repo_cert_utils = RepoCertUtils(self.config)
        self.auth_api = AuthApi()
        self.user_api = UserApi()
        self.clean()
        sn = SerialNumber()
        sn.reset()

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

    def test_enable_global_repo_auth(self):
        '''
        Tests that enabling global repo auth correctly saves the bundle and informs
        the CDS instances of the change.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        # Test
        self.auth_api.enable_global_repo_auth(bundle)

        # Verify
        read_bundle = self.repo_cert_utils.read_global_cert_bundle()

        self.assertTrue(read_bundle is not None)
        self.assertEqual(read_bundle, bundle)

    def test_disable_global_repo_auth(self):
        '''
        Tests that disabling global repo auth correctly removes the bundle and informs
        the CDS instances of the change.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}
        self.auth_api.enable_global_repo_auth(bundle)

        # Test
        self.auth_api.disable_global_repo_auth()

        # Verify
        read_bundle = self.repo_cert_utils.read_global_cert_bundle()
        self.assertTrue(read_bundle is None)
