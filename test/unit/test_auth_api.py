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
import shutil
import sys
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import mocks
from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.server.api.auth import AuthApi
from pulp.server.api.cds import CdsApi
from pulp.server.api.user import UserApi
from pulp.server.auth import principal
import pulp.server.auth.cert_generator as cert_generator
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server.auth.certificate import Certificate
from pulp.server.agent import CdsAgent

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
        self.cds_api.clean()
        testutil.common_cleanup()
        mocks.reset()

    def setUp(self):
        mocks.install()
        self.config = testutil.load_test_config()
        self.config.set('repos', 'cert_location', CERT_DIR)
        self.config.set('repos', 'global_cert_location', GLOBAL_CERT_DIR)
        self.repo_cert_utils = RepoCertUtils(self.config)
        self.auth_api = AuthApi()
        self.user_api = UserApi()
        self.cds_api = CdsApi()
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
        hostnames = ('cds1', 'cds2')
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        cdslist = []
        for hostname in hostnames:
            cds = self.cds_api.register(hostname)
            cdslist.append(cds)

        # reset call history
        mocks.reset()

        # Test
        successes, failures = self.auth_api.enable_global_repo_auth(bundle)

        # Verify
        read_bundle = self.repo_cert_utils.read_global_cert_bundle()

        self.assertTrue(read_bundle is not None)
        self.assertEqual(read_bundle, bundle)

        self.assertEqual(2, len(successes))
        self.assertEqual(0, len(failures))
        
        # Verify
        #  Each cds got called with set_global_repo_auth() and
        #  sent the expected bundle.
        for cds in cdslist:
            agent = CdsAgent(cds)
            cdsplugin = agent.cdsplugin()
            calls = cdsplugin.set_global_repo_auth.history()
            lastcall = calls[-1]
            sentbundle = lastcall[0][0]
            self.assertEqual(1, len(calls)) # one per CDS
            self.assertEqual(sentbundle, bundle)

    def test_enable_global_repo_auth_no_cds(self):
        '''
        Tests the simpler case of having no CDS instances present when enabling
        repo auth (make sure errors aren't thrown when trying to notify a non-existent
        list of CDS instances).
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        # Test
        successes, failures = self.auth_api.enable_global_repo_auth(bundle)

        # Verify
        read_bundle = self.repo_cert_utils.read_global_cert_bundle()

        self.assertTrue(read_bundle is not None)
        self.assertEqual(read_bundle, bundle)

        self.assertEqual(0, len(successes))
        self.assertEqual(0, len(failures))

    def test_enable_global_repo_auth_failed_cds(self):
        '''
        Tests the results of enabling global repo auth when a CDS fails to update.
        '''

        # Setup
        hostnames = ('cds1', 'cds2')
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        cdslist = []
        for hostname in hostnames:
            cds = self.cds_api.register(hostname)
            cdslist.append(cds)

        # configure each cds agent to raise an exception in the
        # next set_global_repo_auth() call.
        for cds in cdslist:
            agent = CdsAgent(cds)
            cdsplugin = agent.cdsplugin()
            calls = cdsplugin.set_global_repo_auth.push(Exception())

        # Test
        successes, failures = self.auth_api.enable_global_repo_auth(bundle)

        # Verify
        read_bundle = self.repo_cert_utils.read_global_cert_bundle()

        self.assertTrue(read_bundle is not None)
        self.assertEqual(read_bundle, bundle)

        self.assertEqual(0, len(successes))
        self.assertEqual(2, len(failures))

    def test_disable_global_repo_auth(self):
        '''
        Tests that disabling global repo auth correctly removes the bundle and informs
        the CDS instances of the change.
        '''

        # Setup
        hostnames = ('cds1', 'cds2')
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}
        self.auth_api.enable_global_repo_auth(bundle)

        cdslist = []
        for hostname in hostnames:
            cds = self.cds_api.register(hostname)
            cdslist.append(cds)

        # reset call history
        mocks.reset()

        # Test
        successes, failures = self.auth_api.disable_global_repo_auth()

        # Verify
        read_bundle = self.repo_cert_utils.read_global_cert_bundle()
        self.assertTrue(read_bundle is None)

        self.assertEqual(2, len(successes))
        self.assertEqual(0, len(failures))
                
        # Verify
        #  Each cds got called with set_global_repo_auth() and
        #  sent the expected bundle.
        for cds in cdslist:
            agent = CdsAgent(cds)
            cdsplugin = agent.cdsplugin()
            calls = cdsplugin.set_global_repo_auth.history()
            lastcall = calls[-1]
            sentbundle = lastcall[0][0]
            self.assertEqual(1, len(calls)) # one per CDS
            self.assertEqual(sentbundle, None)

    def test_disable_global_repo_auth_no_cds(self):
        '''
        Tests the simpler case of having no CDS instances present when disabling global
        repo auth.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}
        self.auth_api.enable_global_repo_auth(bundle)

        # Test
        successes, failures = self.auth_api.disable_global_repo_auth()

        # Verify
        read_bundle = self.repo_cert_utils.read_global_cert_bundle()
        self.assertTrue(read_bundle is None)

        self.assertEqual(0, len(successes))
        self.assertEqual(0, len(failures))

    def test_disable_global_repo_auth_failed_cds(self):
        '''
        Tests the results of disabling global repo auth when a CDS fails to update.
        '''

        # Setup
        hostnames = ('cds1', 'cds2')
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}
        self.auth_api.enable_global_repo_auth(bundle)

        cdslist = []
        for hostname in hostnames:
            cds = self.cds_api.register(hostname)
            cdslist.append(cds)

        # configure each cds agent to raise an exception in the
        # next set_global_repo_auth() call.
        for cds in cdslist:
            agent = CdsAgent(cds)
            cdsplugin = agent.cdsplugin()
            calls = cdsplugin.set_global_repo_auth.push(Exception())

        # Test
        successes, failures = self.auth_api.disable_global_repo_auth()

        # Verify
        read_bundle = self.repo_cert_utils.read_global_cert_bundle()
        self.assertTrue(read_bundle is None)

        self.assertEqual(0, len(successes))
        self.assertEqual(2, len(failures))
