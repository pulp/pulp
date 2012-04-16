#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
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
import shutil
import sys
import os
import urlparse
from M2Crypto import X509

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp.repo_auth.oid_validation as oid_validation
from pulp.repo_auth.oid_validation import OidValidator
from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.server.api.repo import RepoApi
from pulp.server.api.auth import AuthApi

# -- constants ------------------------------------------------------------------

CERT_TEST_DIR = '/tmp/test_oid_validation/'

# -- mocks ----------------------------------------------------------------------

def mock_environ(client_cert_pem, uri):
    environ = {}
    environ["mod_ssl.var_lookup"] = lambda *args: client_cert_pem
    # Set REQUEST_URI the same way that it will be set via mod_wsgi
    path = urlparse.urlparse(uri)[2]
    environ["REQUEST_URI"] = path
    
    class Errors:
        def write(self, *args, **kwargs):
            pass

    environ["wsgi.errors"] = Errors()
    return environ

# -- test cases -----------------------------------------------------------------

class TestOidValidation(testutil.PulpAsyncTest):

    def clean(self):
        testutil.PulpAsyncTest.clean(self)
        if os.path.exists(CERT_TEST_DIR):
            shutil.rmtree(CERT_TEST_DIR)

        protected_repo_listings_file = self.config.get('repos', 'protected_repo_listing_file')
        if os.path.exists(protected_repo_listings_file):
            os.remove(protected_repo_listings_file)

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.validator = OidValidator(self.config)


    def print_debug(self):
        valid_ca = X509.load_cert_string(VALID_CA)
        invalid_ca = X509.load_cert_string(INVALID_CA)
        print "--Reference Values--"
        print "INVALID_CA: %s %s" % (invalid_ca.get_subject(), invalid_ca.get_subject().as_hash())
        print "VALID_CA: %s %s" % (valid_ca.get_subject(), valid_ca.get_subject().as_hash())

    # See https://fedorahosted.org/pulp/wiki/RepoAuth for more information on scenarios
    def simple_m2crypto_verify(self, cert_pem, ca_pem):
        cert = X509.load_cert_string(cert_pem)
        issuer = cert.get_issuer()
        ca_cert = X509.load_cert_string(ca_pem)
        #print "Cert issued by: %s, with hash of: %s" % (issuer, issuer.as_hash())
        #print "CA is: %s, with hash of: %s" % (ca_cert.get_subject(), ca_cert.get_subject().as_hash())
        return cert.verify(ca_cert.get_pubkey())

    def test_basic_validate(self):
        self.auth_api.disable_global_repo_auth()
        repo_cert_utils = RepoCertUtils(config=self.config)

        cert_pem = FULL_CLIENT_CERT
        ca_pem = VALID_CA
        status = repo_cert_utils.validate_certificate_pem(cert_pem, ca_pem)
        self.assertTrue(status)
        status = self.simple_m2crypto_verify(cert_pem, ca_pem)
        self.assertTrue(status)

        cert_pem = FULL_CLIENT_CERT
        ca_pem = INVALID_CA
        status = repo_cert_utils.validate_certificate_pem(cert_pem, ca_pem)
        self.assertFalse(status)
        status = self.simple_m2crypto_verify(cert_pem, ca_pem)
        self.assertFalse(status)

        cert_pem = ANYCERT
        ca_pem = VALID_CA
        status = repo_cert_utils.validate_certificate_pem(cert_pem, ca_pem)
        self.assertFalse(status)
        status = self.simple_m2crypto_verify(cert_pem, ca_pem)
        self.assertFalse(status)


    def test_scenario_1(self):
        '''
        Setup
        - Global auth disabled
        - Individual repo auth enabled for repo X
        - Client cert signed by repo X CA
        - Client cert has entitlements

        Expected
        - Permitted for both repos
        '''

        # Setup
        self.auth_api.disable_global_repo_auth()

        repo_x_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(FULL_CLIENT_CERT, 'https://localhost//pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(FULL_CLIENT_CERT, 'https://localhost//pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(response_y)

    def test_scenario_2(self):
        '''
        Setup
        - Global auth disabled
        - Individual repo auth enabled for repo X
        - Client cert signed by different CA than repo X
        - Client cert has entitlements

        Expected
        - Denied to repo X, permitted for repo Y
        '''

        # Setup
        self.auth_api.disable_global_repo_auth()

        repo_x_bundle = {'ca' : INVALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(response_y)

    def test_scenario_3(self):
        '''
        Setup
        - Global auth disabled
        - Individual repo auth enabled for repo X
        - Client cert signed by repo Y CA
        - Client cert does not have entitlements for requested URL

        Expected
        - Permitted to repo X, denied from repo Y
        '''

        # Setup
        self.auth_api.disable_global_repo_auth()

        repo_y_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch', consumer_cert_data=repo_y_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(LIMITED_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(LIMITED_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(not response_y)

    def test_scenario_4(self):
        '''
        Setup
        - Global auth enabled
        - Individual auth disabled
        - Client cert signed by global CA
        - Client cert has entitlements to both repo X and Y

        Expected
        - Permitted to repo X and Y
        '''

        # Setup
        global_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT,}
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(response_y)

    def test_scenario_5(self):
        '''
        Setup
        - Global auth enabled
        - Individual auth disabled
        - Client cert signed by global CA
        - Client cert has entitlements to only repo X

        Expected
        - Permitted to repo X, denied to repo Y
        '''

        # Setup
        global_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(LIMITED_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(LIMITED_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(not response_y)

    def test_scenario_6(self):
        '''
        Setup
        - Global auth enabled
        - Individual auth disabled
        - Client cert signed by non-global CA
        - Client cert has entitlements for both repos

        Expected
        - Denied to both repo X and Y
        '''

        # Setup
        global_bundle = {'ca' : INVALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(not response_y)

    def test_scenario_7(self):
        '''
        Setup
        - Global auth enabled
        - Individual auth enabled on repo X
        - Both global and individual auth use the same CA
        - Client cert signed by the specified CA
        - Client cert has entitlements for both repos

        Expected
        - Permitted for both repo X and Y
        '''

        # Setup
        global_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(response_y)

    def test_scenario_8(self):
        '''
        Setup
        - Global auth enabled
        - Individual auth enabled on repo X
        - Different CA certificates for global and repo X configurations
        - Client cert signed by repo X's CA certificate
        - Client cert has entitlements for both repos

        Expected
        - Permitted for repo X, denied for repo Y
        '''

        # Setup
        global_bundle = {'ca' : INVALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(not response_y)

    def test_scenario_9(self):
        '''
        Setup
        - Global auth enabled
        - Individual auth enabled for repo X
        - Different CA certificates for global and repo X configurations
        - Client cert signed by global CA certificate
        - Client cert has entitlements for both repos

        Excepted
        - Denied for repo X, passes for repo Y
        '''

        # Setup
        global_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca' : INVALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(response_y)

    def test_scenario_10(self):
        '''
        Setup
        - Global auth disabled
        - Individual repo auth enabled for repo X
        - No client cert in request

        Expected
        - Denied for repo X, permitted for repo Y
        - No exceptions thrown
        '''

        # Setup
        self.auth_api.disable_global_repo_auth()

        repo_x_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(response_y)

    def test_scenario_11(self):
        '''
        Setup
        - Global auth enabled
        - Individual auth disabled
        - No client cert in request

        Expected
        - Denied to both repo X and Y
        - No exceptions thrown
        '''

        # Setup
        global_bundle = {'ca' : INVALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(not response_y)

    def test_scenario_12(self):
        '''
        Setup
        - Global auth enabled
        - Individual auth enabled on repo X
        - Both global and individual auth use the same CA
        - No client cert in request

        Expected
        - Denied for both repo X and Y
        - No exceptions thrown
        '''

        # Setup
        global_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca' : VALID_CA, 'key' : ANYKEY, 'cert' : ANYCERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(not response_y)

    def test_scenario_13(self):
        repo_x_bundle = {'ca' : VALID_CA2, 'key' : ANYKEY2, 'cert' : ANYCERT2, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(FULL_WILDCARD_CLIENT, 
            'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/os')
        request_y = mock_environ(FULL_WILDCARD_CLIENT, 
            'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/os')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(response_y)

        # Try to hit something that should be denied
        request_z = mock_environ(FULL_WILDCARD_CLIENT, 
            'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/mrg-g/2.0/os')
        response_z = oid_validation.authenticate(request_z, config=self.config)
        self.assertTrue(not response_z)

    def test_scenario_14(self):
        '''
        Setup
        - Global auth disabled
        - Individual repo auth enabled for repo X
        - Client cert signed by repo X CA
        - Client cert has an OID entitlement that ends with a yum variable.
          e.g., repos/pulp/pulp/fedora-14/$basearch/

        Expected
        - Permitted for both repos
        '''

        # Setup
        self.auth_api.disable_global_repo_auth()

        repo_x_bundle = {'ca' : VALID_CA2, 'key' : VALID_CA2_KEY, 'cert' : ANYCERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(ENDS_WITH_VARIABLE_CLIENT +
            ENDS_WITH_VARIABLE_CLIENT_KEY, 
            'https://localhost//pulp/repos/repos/pulp/pulp/fedora-14/x86_64/os/repodata/repomd.xml')
        request_xx = mock_environ(ENDS_WITH_VARIABLE_CLIENT +
            ENDS_WITH_VARIABLE_CLIENT_KEY, 
            'https://localhost//pulp/repos/repos/pulp/pulp/fedora-14/i386/os/repodata/repomd.xml')
        request_y = mock_environ(ENDS_WITH_VARIABLE_CLIENT +
            ENDS_WITH_VARIABLE_CLIENT_KEY, 
            'https://localhost//pulp/repos/repos/pulp/pulp/fedora-13/x86_64/os/repodata/repomd.xml')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_xx = oid_validation.authenticate(request_xx, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(response_y)


# -- test data ---------------------------------------------------------------------

ANYCERT = """
-----BEGIN CERTIFICATE-----
MIIC9zCCAd8CAmlJMA0GCSqGSIb3DQEBBQUAMG4xCzAJBgNVBAYTAlVTMRAwDgYD
VQQIEwdBbGFiYW1hMRMwEQYDVQQHEwpIdW50c3ZpbGxlMRYwFAYDVQQKEw1SZWQg
SGF0LCBJbmMuMSAwHgYJKoZIhvcNAQkBFhFqb3J0ZWxAcmVkaGF0LmNvbTAeFw0x
MTA2MDMyMDQ5MjdaFw0yMTA1MzEyMDQ5MjdaMBQxEjAQBgNVBAMTCWxvY2FsaG9z
dDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMRkjseAow6eH/IgWb5z
D47QRA0No9jNqGL6onRSYaMjCTKcu3T1nPbBTVlxSQw9cah2anXoJaFZzIcc7c0R
PGMpJR3wVe/0sOBMTeD0CFHwdhin2lo75AMLldc/7qenuMT9bxaQKZ3MDRbalz+E
SIXFZPx/Oy2cp5vWwq3OEQAcRwMhdYZfRjoKZ+xQ+kHhdJD4Baakee8vyP2o3T+x
LY2ZOBBLtuhypB96QrCESozL8u2YS3Dqbq1X0ge0eub/lk+QMDjrtF5kTC45jgJE
ykdRFhgKznO5IAwnHt5NvZ1wQxF/lAvt6lBG5t9XuFV1cQOLiE7BzklDjOX97Oy9
JxMCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEAZwck2cMAT/bOv9Xnyjx8qzko2xEm
RlHtMDMHpzBGLRAaj9Pk5ckZKJLeGNnGUXTEA2xLfN5Q7B9R9Cd/+G3NE2Fq1KfF
XXPux/tB+QiSzzrE2U4iOKDtnVEHAdsVI8fvFZUOQCr8ivGjdWyFPvaRKI0wA3+s
XQcarTMvR4adQxUp0pbf8Ybg2TVIRqQSUc7gjYcD+7+ThuyWLlCHMuzIboUR+NRa
kdEiOVJc9jJOzj/4NljtFggxR8BV5QbCt3w2rRhmnhk5bN6OdqxbJjH8Wmm6ae0H
rwlofisIJvB0JQxaoQgprDem4CChLqEAnMmCpybfSLLqXTieTPr116nQ9A==
-----END CERTIFICATE-----
"""

ANYKEY = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAxGSOx4CjDp4f8iBZvnMPjtBEDQ2j2M2oYvqidFJhoyMJMpy7
dPWc9sFNWXFJDD1xqHZqdegloVnMhxztzRE8YyklHfBV7/Sw4ExN4PQIUfB2GKfa
WjvkAwuV1z/up6e4xP1vFpApncwNFtqXP4RIhcVk/H87LZynm9bCrc4RABxHAyF1
hl9GOgpn7FD6QeF0kPgFpqR57y/I/ajdP7EtjZk4EEu26HKkH3pCsIRKjMvy7ZhL
cOpurVfSB7R65v+WT5AwOOu0XmRMLjmOAkTKR1EWGArOc7kgDCce3k29nXBDEX+U
C+3qUEbm31e4VXVxA4uITsHOSUOM5f3s7L0nEwIDAQABAoIBAQCxBnt09U0FZh8h
n2uFsi15690Lbxob2PVJkuZQt9lutawaxRBsEuETw5Y3Y1gXAmOrGGJKOaGB2XH0
8GyiBkFKmNHuNK8iBoxRAjbI6O9+/KNXAiZeY9HZtN2yEtzKnvJ8Dn3N9tCsfjvm
N89R36mHezDWMNFlAepLHMCK7k6Aq2XfMSgHJMmHYv2bBdcnbPidl3kr8Iq3FLL2
0qoiou+ihvKEj4SAguQNuR8w5oXKc5I3EdmXGGJ0WlZM2Oqg7qL85KhQTg3WEeUj
XB4cLC4WoV0ukvUBuaCFCLdqOLmHk2NB3b4DEYlEIsz6XiE3Nt7cBO2HBPa/nTFl
qAvXxQchAoGBAPpY1S1SMHEWH2U/WH57jF+Yh0yKPPxJ6UouG+zzwvtm0pfg7Lkn
CMDxcTTyMpF+HjU5cbJJrVO/S1UBnWfxFdbsWFcw2JURqXj4FO4J5OcVHrQEA6KY
9HBdPV6roTYVIUeKZb6TxIC85b/Xkcb3AHYtlDg3ygOjFKD6NUVNHIebAoGBAMjT
1bylHJXeqDEG+N9sa1suH7nMVsB2PdhsArP3zZAoOIP3lLAdlQefTyhpeDgYbFqD
wxjeFHDuJjxIvB17rPCKa8Rh4a0GBlhKEDLm+EM3H0FyZ0Yc53dckgDOnJmyh9f+
8fc7nYqXEA7sD0keE9ANGS+SLV9h9v9A7og7bGHpAoGAU/VU0RU+T77GmrMK36hZ
pHnH7mByIX48MfeSv/3kR2HtgKgbW+D+a47Nk58iXG76fIkeW1egPHTsM78N5h0R
YPn0ipFEIYJB3uL8SfShguovWNn7yh0X5VMv0L8omrWtaou8oZR3E2HGf3cxWZPe
4MNacRwssNmRgodHNE2vIr8CgYABp50vPL0LjxYbsU8DqEUKL0sboM9mLpM74Uf0
a6pJ8crla3jSKqw7r9hbIONYsvrRlBxbbBkHBS9Td9X0+Dvoj3tr1tKhNld/Cr0v
bi/FfgLH60Vmkn5lwWGCmDE6IvpzkSo1O0yFA9GiDdfiZlkLcdAvUCkHjCsY11Qf
0z2FYQKBgQDCbtiEMMHJGICwEX2eNiIfO4vMg1qgzYezJvDej/0UnqnQjbr4OSHf
0mkVJrA0vycI+lP94eEcAjhFZFjCKgflZL9z5GLPv+vANbzOHyIw+BLzX3SybBeW
NgH6CEPkQzXt83c+B8nECNWxheP1UkerWfe/gmwQmc0Ntt4JvKeOuw==
-----END RSA PRIVATE KEY-----
"""

# Entitlements for:
#  - repos/pulp/pulp/fedora-14/x86_64/
LIMITED_CLIENT_CERT = '''
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAzlWuSKJaNxamjwdAf4RUoDNLl9T2DV8ls4FZ3l3cGIQEftdL
+YHPe2nn3VZGEqHVWyEQcIvkgu0ErltYKVHbGP38la6ZkgeFcrM4J/u1T8XC4ZWN
22ByrurDYVgUO/t/WObNtbEa5kdT26AvcnUu13kS6Xn8nGnWCo/AjIjf1DCOhf/L
ig7KcjmdZtPJ43PJM2VMkdyE6R54J0SPlFbU6lPXD4ScAWblJ1x4zN/Tm4r/I65q
44JtYcRllrwGGhpHeYRxEdDcsv1nkp1ssVEj3i0lijD8EZD84LjhWU2tHrQefkIN
wYzeO2TYlUMOkLk6Ik7SaT7M4CPq8GdHMQUeBQIDAQABAoIBAChlkAS6fI0yixOP
qOoOX38p68/jKvU9PqVhWtX1bGUEW9j1j/Nend+cwX+NJ5T4SExaMdzHFssnWnZE
fgNA+nNvLqejkn+Lp23odsMlPb9Libcez7I2tN1YKz6Avx1rROiD75x1+z1Ak8N5
HjD7jlszYieB8ZoyAmz47grVtXTWXtpEY/ut5lfTtUUBi6SwqTHiEKIoWrbkAZga
e8r8iRgAdMWCPNJIV3GnicvVd2vehGJEn73eoCrN9AVGrgGfH386HC0NPNGkgFGZ
+rJO7pwv7fy10PEbnz1BMoIMLjYi9qZGXgGNCsaCzF/ioHyNEGBTD7cHMg8DyXJd
3YNI7aECgYEA7AehN7anc/6xWLRUotZGTaPaay6673NeB+upTBBFOY/mRDzAYK/M
aMFFV+xQbzUH7P8Xa/nlKKw6rslP4WwyWSReSY3fdHv3llq0e3Yea2znqycSIs2Y
ai17p0o+FF+pMlsfn8GmZFAeH+8m223h1ESUGO4zulLrMDMEm6tssb0CgYEA38rb
/RwCmenTJSOvrpk2YibAR9/jqAe0Lav+JXWTyjqdM+TXsq3ljLMLWRLaYq2KjDYq
xxPxyHEFf26UAEgM0bwgo8BUFzaoPqGgwE3SCUjHVw9Y6j7zrY69JEliyj1z+ObM
3wwmUKr7AccwpI7PFFsTumqlDsvpsQ9miwR/zekCgYEAw6kvhDfuaMHh0l7rKnHm
pcYG8oMyg/1nHbnGBkAWorkfccHK2FvjX5OYIGLN6uJTR6vPhrsJtMXRf8NybLR8
qFj1sJPjgXSisglPRGmOng8RnVguOJumlZ5Ou0dYXxtN72iKtqyZet7PmjluRMi6
RHT1MBWG3BaQ0Mv6LfHVkSECgYBckEiLmWFODhPiYa9RtVd0I3kWgXllT8JrvZ8C
GW7Gj5XkF/xLkHfIyWmhLxYbCJKsyd7Jtusjr/PJMJCQyTxcJ8cMVAm0DExsk2et
AsMkSfEBhnyNbvpVSBvdfWkaI27rfXMxspHKfd4SbzQkbFkkn0M6sM+Sni8LqEYO
rA68uQKBgFqmuzi7DlQrojK8hcETeXlQavQtQvBow1L2hxlYNFyb6GnwCgfHDHNY
yQIWIr6fjfLU4mgBPk7RGkFNvIcK3GKKwSwFiJWsWcOSStkTLOq6QMlJBGtpwM3B
MK9V5QFftHd8/Y1u1nTVMVe35Xu02kOG+BB+J907d4yyGRqSGhkD
-----END RSA PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDvDCCAqSgAwIBAgIBCzANBgkqhkiG9w0BAQUFADBhMQswCQYDVQQGEwJVUzEL
MAkGA1UECAwCTkoxEjAQBgNVBAcMCU1pY2tsZXRvbjEQMA4GA1UECgwHUmVkIEhh
dDENMAsGA1UECwwEUHVscDEQMA4GA1UEAwwHcHVscC1jYTAeFw0xMjAzMjgyMTM4
MTRaFw0xNjAzMjcyMTM4MTRaMGUxCzAJBgNVBAYTAlVTMQswCQYDVQQIDAJOSjES
MBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQKDAdSZWQgSGF0MQ0wCwYDVQQLDARQ
dWxwMRQwEgYDVQQDDAtwdWxwLXNlcnZlcjCCASIwDQYJKoZIhvcNAQEBBQADggEP
ADCCAQoCggEBAM5VrkiiWjcWpo8HQH+EVKAzS5fU9g1fJbOBWd5d3BiEBH7XS/mB
z3tp591WRhKh1VshEHCL5ILtBK5bWClR2xj9/JWumZIHhXKzOCf7tU/FwuGVjdtg
cq7qw2FYFDv7f1jmzbWxGuZHU9ugL3J1Ltd5Eul5/Jxp1gqPwIyI39QwjoX/y4oO
ynI5nWbTyeNzyTNlTJHchOkeeCdEj5RW1OpT1w+EnAFm5SdceMzf05uK/yOuauOC
bWHEZZa8BhoaR3mEcRHQ3LL9Z5KdbLFRI94tJYow/BGQ/OC44VlNrR60Hn5CDcGM
3jtk2JVDDpC5OiJO0mk+zOAj6vBnRzEFHgUCAwEAAaN7MHkwCQYDVR0TBAIwADAa
Bg0rBgEEAZIICQKrAAEBBAkMB1B1bHAtMTQwGgYNKwYBBAGSCAkCqwIBAgQJDAdw
dWxwLTE0MDQGDSsGAQQBkggJAqp9AQYEIwwhcmVwb3MvcHVscC9wdWxwL2ZlZG9y
YS0xNC94ODZfNjQvMA0GCSqGSIb3DQEBBQUAA4IBAQBGgEv0IADcr5z7/g2FOT3a
BbzlXB2zxgttvCANHmLswDZcjD5HPp2ia2u6jswbgt83sQGW8rPMXrGPFr6NFORG
Hv9bik+rul/CtTtPLGthahbGZ/xzqqMV1BXgwiKwF+v6A/XK646vUKctHkdYWzcd
gAjz5TscEVKvTQXVLVGYcbTAWYiNl5ZSZVEPAjSv0DDsNF/8YNjTCL29pgYBRKR2
aSrnqfN9mTqtXJ98Wg+ZUn+r6F6lf1Oo+fUM7jEVaWrSTchpW7QdN2HxDM6D63eh
PHcxz1yg+aO6XvkwZJKygs4snZUu0R1r/7HTaoSEqsCD5Tg/kRaUq9Fab0HIuAbF
-----END CERTIFICATE-----
'''

# Entitlements for:
#  - repos/pulp/pulp/fedora-13/x86_64/
#  - repos/pulp/pulp/fedora-14/x86_64/
FULL_CLIENT_CERT = '''
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAzlWuSKJaNxamjwdAf4RUoDNLl9T2DV8ls4FZ3l3cGIQEftdL
+YHPe2nn3VZGEqHVWyEQcIvkgu0ErltYKVHbGP38la6ZkgeFcrM4J/u1T8XC4ZWN
22ByrurDYVgUO/t/WObNtbEa5kdT26AvcnUu13kS6Xn8nGnWCo/AjIjf1DCOhf/L
ig7KcjmdZtPJ43PJM2VMkdyE6R54J0SPlFbU6lPXD4ScAWblJ1x4zN/Tm4r/I65q
44JtYcRllrwGGhpHeYRxEdDcsv1nkp1ssVEj3i0lijD8EZD84LjhWU2tHrQefkIN
wYzeO2TYlUMOkLk6Ik7SaT7M4CPq8GdHMQUeBQIDAQABAoIBAChlkAS6fI0yixOP
qOoOX38p68/jKvU9PqVhWtX1bGUEW9j1j/Nend+cwX+NJ5T4SExaMdzHFssnWnZE
fgNA+nNvLqejkn+Lp23odsMlPb9Libcez7I2tN1YKz6Avx1rROiD75x1+z1Ak8N5
HjD7jlszYieB8ZoyAmz47grVtXTWXtpEY/ut5lfTtUUBi6SwqTHiEKIoWrbkAZga
e8r8iRgAdMWCPNJIV3GnicvVd2vehGJEn73eoCrN9AVGrgGfH386HC0NPNGkgFGZ
+rJO7pwv7fy10PEbnz1BMoIMLjYi9qZGXgGNCsaCzF/ioHyNEGBTD7cHMg8DyXJd
3YNI7aECgYEA7AehN7anc/6xWLRUotZGTaPaay6673NeB+upTBBFOY/mRDzAYK/M
aMFFV+xQbzUH7P8Xa/nlKKw6rslP4WwyWSReSY3fdHv3llq0e3Yea2znqycSIs2Y
ai17p0o+FF+pMlsfn8GmZFAeH+8m223h1ESUGO4zulLrMDMEm6tssb0CgYEA38rb
/RwCmenTJSOvrpk2YibAR9/jqAe0Lav+JXWTyjqdM+TXsq3ljLMLWRLaYq2KjDYq
xxPxyHEFf26UAEgM0bwgo8BUFzaoPqGgwE3SCUjHVw9Y6j7zrY69JEliyj1z+ObM
3wwmUKr7AccwpI7PFFsTumqlDsvpsQ9miwR/zekCgYEAw6kvhDfuaMHh0l7rKnHm
pcYG8oMyg/1nHbnGBkAWorkfccHK2FvjX5OYIGLN6uJTR6vPhrsJtMXRf8NybLR8
qFj1sJPjgXSisglPRGmOng8RnVguOJumlZ5Ou0dYXxtN72iKtqyZet7PmjluRMi6
RHT1MBWG3BaQ0Mv6LfHVkSECgYBckEiLmWFODhPiYa9RtVd0I3kWgXllT8JrvZ8C
GW7Gj5XkF/xLkHfIyWmhLxYbCJKsyd7Jtusjr/PJMJCQyTxcJ8cMVAm0DExsk2et
AsMkSfEBhnyNbvpVSBvdfWkaI27rfXMxspHKfd4SbzQkbFkkn0M6sM+Sni8LqEYO
rA68uQKBgFqmuzi7DlQrojK8hcETeXlQavQtQvBow1L2hxlYNFyb6GnwCgfHDHNY
yQIWIr6fjfLU4mgBPk7RGkFNvIcK3GKKwSwFiJWsWcOSStkTLOq6QMlJBGtpwM3B
MK9V5QFftHd8/Y1u1nTVMVe35Xu02kOG+BB+J907d4yyGRqSGhkD
-----END RSA PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIEJjCCAw6gAwIBAgIBDDANBgkqhkiG9w0BAQUFADBhMQswCQYDVQQGEwJVUzEL
MAkGA1UECAwCTkoxEjAQBgNVBAcMCU1pY2tsZXRvbjEQMA4GA1UECgwHUmVkIEhh
dDENMAsGA1UECwwEUHVscDEQMA4GA1UEAwwHcHVscC1jYTAeFw0xMjAzMjgyMTQ4
MDVaFw0xNjAzMjcyMTQ4MDVaMGUxCzAJBgNVBAYTAlVTMQswCQYDVQQIDAJOSjES
MBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQKDAdSZWQgSGF0MQ0wCwYDVQQLDARQ
dWxwMRQwEgYDVQQDDAtwdWxwLXNlcnZlcjCCASIwDQYJKoZIhvcNAQEBBQADggEP
ADCCAQoCggEBAM5VrkiiWjcWpo8HQH+EVKAzS5fU9g1fJbOBWd5d3BiEBH7XS/mB
z3tp591WRhKh1VshEHCL5ILtBK5bWClR2xj9/JWumZIHhXKzOCf7tU/FwuGVjdtg
cq7qw2FYFDv7f1jmzbWxGuZHU9ugL3J1Ltd5Eul5/Jxp1gqPwIyI39QwjoX/y4oO
ynI5nWbTyeNzyTNlTJHchOkeeCdEj5RW1OpT1w+EnAFm5SdceMzf05uK/yOuauOC
bWHEZZa8BhoaR3mEcRHQ3LL9Z5KdbLFRI94tJYow/BGQ/OC44VlNrR60Hn5CDcGM
3jtk2JVDDpC5OiJO0mk+zOAj6vBnRzEFHgUCAwEAAaOB5DCB4TAJBgNVHRMEAjAA
MBkGDCsGAQQBkggJAgEBAQQJDAdQdWxwLTE0MBkGDCsGAQQBkggJAgEBAgQJDAdw
dWxwLTE0MDMGDCsGAQQBkggJAgEBBgQjDCFyZXBvcy9wdWxwL3B1bHAvZmVkb3Jh
LTE0L3g4Nl82NC8wGQYMKwYBBAGSCAkCAgEBBAkMB1B1bHAtMTMwGQYMKwYBBAGS
CAkCAgECBAkMB3B1bHAtMTMwMwYMKwYBBAGSCAkCAgEGBCMMIXJlcG9zL3B1bHAv
cHVscC9mZWRvcmEtMTMveDg2XzY0LzANBgkqhkiG9w0BAQUFAAOCAQEAPgxmhoFk
FnrCAqrGoJb2NLnsvKhMJSG5v9x/52zWZ+TdvRZh35T1NF8Ibchf1CtRAG3ZaiW5
iehDNNzVxhkCtK4XztTTCOZlI7b6nA1pvfRw68c7unWje2LCZ1iQV37uctpjCSvF
rImdOQqViNA4+dVR34Hi3nn/erV03/B/U5b0+61yMJF1/jNzz/kJJsFo/z/b/H2i
5m4pFs9kkrS6FxDcT9nJ0BSypUW0CQuDtyL5S/fkiK+ESzq91SxVG0hL49+mrhne
ZETguXV3S7g39cQJFcrMLccNFaF9ScPp0DH58FvgjUoFVvP9CoUJlJBSqQBNnVCH
5chAbUWpU9vj/w==
-----END CERTIFICATE-----
'''

VALID_CA = '''
-----BEGIN CERTIFICATE-----
MIIDlTCCAn2gAwIBAgIJAP+15ciSiPzeMA0GCSqGSIb3DQEBBQUAMGExCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQK
DAdSZWQgSGF0MQ0wCwYDVQQLDARQdWxwMRAwDgYDVQQDDAdwdWxwLWNhMB4XDTEy
MDMyODIxMDczMVoXDTE2MDMyNzIxMDczMVowYTELMAkGA1UEBhMCVVMxCzAJBgNV
BAgMAk5KMRIwEAYDVQQHDAlNaWNrbGV0b24xEDAOBgNVBAoMB1JlZCBIYXQxDTAL
BgNVBAsMBFB1bHAxEDAOBgNVBAMMB3B1bHAtY2EwggEiMA0GCSqGSIb3DQEBAQUA
A4IBDwAwggEKAoIBAQC4fIQQ3Rx9y0x0/GdZeD+xypzh8ytQBX7nLavBp0sslF5G
xWyO2kBq4NY3LtQOxPamDpWQck4eBps/6ajMTeC09hKHxXCHcD2Ivx/kO72bev6z
gSVKUSJnu1AF4fIlQl/nxodKz6XwSR4C9+GfK9jNP6NUFQKGsQ3/FHDCvEUkdkG9
SDXfxRRq6FTAl+Owt7JXIGzosbU6d8mZoqpRx6AZ+kA7Bas2lBG0km785SMyxjVB
CabS09M0gPzHPBfrucIgvIyw82VJY25UWsa1UkQyfJ/nsuj1WhWJa6XvgtsZfTm4
56mFcFgu3hJ8I0SLvnsTZVoIZoUKMj/h5FwhcBs3AgMBAAGjUDBOMB0GA1UdDgQW
BBQUEhXReUDSCm2ZOrkbOPuFedhl2jAfBgNVHSMEGDAWgBQUEhXReUDSCm2ZOrkb
OPuFedhl2jAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBBQUAA4IBAQABcUhYK9NY
5ew5mlVIzEPgZDdWhDHRutottQb3UQu6c2kHwwJZdzplHaxn5Mo0fqt6JaYbqnbH
goLCHyLpRLBL/Dj/7SFM8xKgkFkLfd4fDOINV6Gec3tIEFBDBG3wcYT5GcFQh+JD
Qga6Lt57gLnkd9G8Y93It1T0pbFQhOh8U+g/jnPjCqFTqOMoAngVPZZTsg26cVh+
12jOyy7kXrKEtLESaj56rFoRtX8QbwknYJ60W8t+n2ZqtCjyNN65RXTFK95TmWSZ
hYMwmwaaUUDm4wSKS/4mmUKFCN8eaCGHKFN47hK66KZ9vRKK3VFOssQ5CIE8o2b7
/Yb4KafFsHUY
-----END CERTIFICATE-----
'''

INVALID_CA = '''
-----BEGIN CERTIFICATE-----
MIIDpTCCAo2gAwIBAgIJAKkrGxLzlBlLMA0GCSqGSIb3DQEBBQUAMGkxCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQK
DAdSZWQgSGF0MQ0wCwYDVQQLDARQdWxwMRgwFgYDVQQDDA9wdWxwLWludmFsaWQt
Y2EwHhcNMTIwNDE2MTM0NTIxWhcNMjUxMjI0MTM0NTIxWjBpMQswCQYDVQQGEwJV
UzELMAkGA1UECAwCTkoxEjAQBgNVBAcMCU1pY2tsZXRvbjEQMA4GA1UECgwHUmVk
IEhhdDENMAsGA1UECwwEUHVscDEYMBYGA1UEAwwPcHVscC1pbnZhbGlkLWNhMIIB
IjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqdGWUTKTf74EsxrT7+XqDh3F
muGiJIRs4BAZPBMCenxxag/FRwtWeR/Z8xovLvlpivOvJiYxDlmQROMH9AbzCT94
qChgre+weel81bWR6gc4fOxUTap4cHA7nwvP5PQP6oUlcn0ZH0fyN/YAj1c0d7Bv
UHyne+C1fxcYIjgouERHWo9P0xv7jpnn2nUxs40B4QDTK+g0Zu4h/KGiEVr6IK+/
ZRO8KCih9UdzVYKG8AjeY0d0LP3eSuX8srcM2RFwFcXh3gpt5aWgcUQR3OjeSHBR
ho/yDXxm52tsD7J5QXvijvu7ILuE7yUVVkCxtOu7POtEKf/aDjQiMh194MZ0gQID
AQABo1AwTjAdBgNVHQ4EFgQUtlwrMUV5vmkU/UJq3xBGCGmQmIMwHwYDVR0jBBgw
FoAUtlwrMUV5vmkU/UJq3xBGCGmQmIMwDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0B
AQUFAAOCAQEABlL6CBQBEqGreP8hvc8mm9YWb4SOZdCreEuewMYdV0tdIiS6rjg6
xoQhAzWmvBVxd0kpm33TAP9mqD9oExrH7WTc+QCRoihW7EcoK5utXAeU8oiuFSSh
zZUBkCBQkDX7QF0twLorfKxfNEuNuUj1anGHEjESadQV++dNl9yvM82JcpqgAuoj
rdAaDQrVVRVpCe5ClJqWJROziEEGj10nsTskjuqXChaslJ2O0iYm6ZPZcmDXOOEj
yF0ir5JjvZQ6zZdo/D+wSdfK1TLl5hjpzFTlElOeOC5XM13pgUfIF3nWeIKJEUyJ
YSMf0fu6BrpTgoyet283Ek9qg8NqKtMv1A==
-----END CERTIFICATE-----
'''


PRE_INVALID_CA = '''
-----BEGIN CERTIFICATE-----
MIIDpTCCAo2gAwIBAgIJAOEkwX9JQSjkMA0GCSqGSIb3DQEBBQUAMGkxCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQK
DAdSZWQgSGF0MQ0wCwYDVQQLDARQdWxwMRgwFgYDVQQDDA9wdWxwLWludmFsaWQt
Y2EwHhcNMTIwMzI4MjEwODMzWhcNMTYwMzI3MjEwODMzWjBpMQswCQYDVQQGEwJV
UzELMAkGA1UECAwCTkoxEjAQBgNVBAcMCU1pY2tsZXRvbjEQMA4GA1UECgwHUmVk
IEhhdDENMAsGA1UECwwEUHVscDEYMBYGA1UEAwwPcHVscC1pbnZhbGlkLWNhMIIB
IjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuHyEEN0cfctMdPxnWXg/scqc
4fMrUAV+5y2rwadLLJReRsVsjtpAauDWNy7UDsT2pg6VkHJOHgabP+mozE3gtPYS
h8Vwh3A9iL8f5Du9m3r+s4ElSlEiZ7tQBeHyJUJf58aHSs+l8EkeAvfhnyvYzT+j
VBUChrEN/xRwwrxFJHZBvUg138UUauhUwJfjsLeyVyBs6LG1OnfJmaKqUcegGfpA
OwWrNpQRtJJu/OUjMsY1QQmm0tPTNID8xzwX67nCILyMsPNlSWNuVFrGtVJEMnyf
57Lo9VoViWul74LbGX05uOephXBYLt4SfCNEi757E2VaCGaFCjI/4eRcIXAbNwID
AQABo1AwTjAdBgNVHQ4EFgQUFBIV0XlA0gptmTq5Gzj7hXnYZdowHwYDVR0jBBgw
FoAUFBIV0XlA0gptmTq5Gzj7hXnYZdowDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0B
AQUFAAOCAQEAbrGKvwcwX8GQBJY9JN3MGT+HNdOba34mpNy3x1ap8VrKzFjJsq1q
bjqUnDBw+9Yc7LEiK6EfY+LMF5oqOsC8J5DzoDvc4qhPoEs7rqkcGBgWQPSn8Qvo
BEtxTPD6XPBTnpIYxBxhlMaG2fdHWdGy2Dvg/LTE76x/U2BggPy4l2FlCsl4Us84
oEw/se7KXjXS5FVjR5JDt0bV2wL8UWeoegoV7qZUzN8hSOuIU7AreUIV6nHtzc11
XpOTiWRV8/L/Bop1rguL5P35HzpP1KJwp6ovQMWKuhGXuBRmHVpGNojgRpPUX/tm
VP/6TMkGufjP5mk2AIH292PKjoYo8873LQ==
-----END CERTIFICATE-----
'''

VALID_CA2 = '''
-----BEGIN CERTIFICATE-----
MIIFlzCCA3+gAwIBAgIJAK7gLD9A4byOMA0GCSqGSIb3DQEBBQUAMGIxCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJOQzEQMA4GA1UEBwwHUmFsZWlnaDEQMA4GA1UECgwH
dGVzdC1jYTEQMA4GA1UECwwHdGVzdC1jYTEQMA4GA1UEAwwHdGVzdC1jYTAeFw0x
MTEwMjQxODM3NDFaFw0zOTAzMTExODM3NDFaMGIxCzAJBgNVBAYTAlVTMQswCQYD
VQQIDAJOQzEQMA4GA1UEBwwHUmFsZWlnaDEQMA4GA1UECgwHdGVzdC1jYTEQMA4G
A1UECwwHdGVzdC1jYTEQMA4GA1UEAwwHdGVzdC1jYTCCAiIwDQYJKoZIhvcNAQEB
BQADggIPADCCAgoCggIBALse+W5GQZbKVlXaWhR/d19KzORVLt141K5YuDUec8yV
wWQjbzaFzCR5PR93078qWTFAhnTjR7L7Q3VN22I47AN7ndX7hB0DjNaXU4glb0L8
U1kgcYn3hn109WHLmBQ6vZh/NDxcrXXJRwLPN3wuxY5H2riEuAyyPO3sIt1GZqgZ
lPAwRVTM/izpQzf1vF8BPQu7BeyKhzy77VViZmnM5VMjOnqVuJHxXVKrJz9sBkWw
gjynn50MDGfMSdTbicBVenEYt8UzJ9BxGfbhOw44f4AUHf0cakewPaauBn+2hNwM
ULprLc+L33sMzHWwXLTJbZY4F/6nc9ocoBU99eBvUSsuIdOixszYKdiGcx+LYRsj
1Y3x1spTmkBAZxAlJP33hnp5XvHYNKqEKf83ysOzmxS9ypL+pSXaZk80CHvOPTAN
qlugMU32avI8E826pILxAxS7M/PO9BjM6d3ll6myghU7rgHWg4J8ppNBGq6nG00s
Zg1rfAy5C7B1DSeTP6X/sW2d/VMvt4IdwJSTKaOlGMQ/xt8BsebMQguQrJNDytpn
Z7G13TPyHsoukaeTh/DjNBEQBBdPXPyRGnZKplrWl6CefVJVnua/t2akKSU0QUwd
LgSWJh66CGq8FnZWzgzimWG63jTqOPFwbC/exQ3HA/wKQm0a92nc03drXLfL9c2P
AgMBAAGjUDBOMB0GA1UdDgQWBBT09Bd6VJIChSReb9CiRJNJFVUxQTAfBgNVHSME
GDAWgBT09Bd6VJIChSReb9CiRJNJFVUxQTAMBgNVHRMEBTADAQH/MA0GCSqGSIb3
DQEBBQUAA4ICAQADUVzB3UtPqWDCaItSjcJzqM4o4ma/c9vIoaiirrM+o1jcNdMF
LKKHrSATG8KVXI//DJBv3VnCnuxUtcFnIgDy7+j0F+WBHQgGab6QHwwMdsnv8UL8
+7BezKzR5kX5tvSaZ6HWuY7fi3Zgy31B8HV5G2FhzFq7m/RUB0ffb/iZb6S4HyZm
XaBAA/Hc+ng9iXSB9ZvyS08xP7jDu2n322FF3xJA9ji20nYfz03VJTrHXe4lapoh
9Ew9qV84gLzVneuxjJ53CplpLD7U3eSiZqK//9TpNflW2vGc/8N9xcX21EX2Mpjn
1A9b9h9MVfptothSeBJodml4F8cMRqmvCq/9gnK2lAWpJhLO3gV94NTIE+2pyX9i
nD9Ts13ng0od5P+C5btCHn4TEACRqUxTM6WknqAgSpx8khOGsj5uljLFRBYEWeRo
xnLEuPaOpXOsfpRcyLsXcTKm/0ixYfaM3O+39seHUiClRT8T9k+0EXEQl6aSIWBB
69FIAf9PZEC+t8aPqA+CRlXw2Xqc1zg7usuPvkxMR/iMhhJ7YTlW8WyFI3BNnQy2
pJ7VHLshUiH3txA3rVlwthJbzuHONzjMKvYzYBeuSIVrri+OWNI1VUeSuDTVz2B4
yJ+DXKvc8zaaoXMu6WxcJOR5p55WZcR93laAMiZSt8YEUltDlrK7G8kVMw==
-----END CERTIFICATE-----
'''

VALID_CA2_KEY = '''
-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----
'''

WILDCARD_CLIENT = '''
-----BEGIN CERTIFICATE-----
MIIF9jCCA96gAwIBAgIJAIgtbC6P/Ds/MA0GCSqGSIb3DQEBBQUAMGIxCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJOQzEQMA4GA1UEBwwHUmFsZWlnaDEQMA4GA1UECgwH
dGVzdC1jYTEQMA4GA1UECwwHdGVzdC1jYTEQMA4GA1UEAwwHdGVzdC1jYTAeFw0x
MTEwMjQxODM5MjBaFw0xMjEwMjMxODM5MjBaMG4xCzAJBgNVBAYTAlVTMQswCQYD
VQQIDAJOQzEQMA4GA1UEBwwHUmFsZWlnaDEUMBIGA1UECgwLdGVzdC1jbGllbnQx
FDASBgNVBAsMC3Rlc3QtY2xpZW50MRQwEgYDVQQDDAt0ZXN0LWNsaWVudDCCAiIw
DQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAPJ0JCG/1hyywObtKbT2Gou0kE8R
v3RwDVSim+NsXnQMawMkut9XePOPuZzxqNm2o3b09WDKlwRaandv4vHKvrkZ/i4q
qjrxBKEjH5jGYQ4MH5mToU9VDSAYC5+c8hjTuwtROtuJn+St9tG+rPwK3htl5hN2
qmNaWG9O5yAOE3qGrP6SZ8uVzrJ3I4zja7tfXIgT6q/VePoDHYkfLW2DrovxEMDs
tXhUhg+NBwr9do+EvazmoirK6aE5b0Knae+wTJKR5fTgQxj8v/DxiMXEbGmu8AKU
mx3y6TyiGavsyAhtY8HAz8B8E0gTPVon91XbKZ07IV1M3aFTYBVHuvbXMtdWFVnB
an6X2WrdCHni+iD5rGbZo4GIowW0v/01whUNhHymqBGR57f+7lJ5v94oSTzeBQ/O
r2TXkxQJyPgAfFXavROV20ZRVewveHpUd8u10nMiJ9NpBjgigS8+Xy8aGZQV96xl
4ul3fsea6h9Yv8Dm1OnJhfSFvZ9NahcxYMTdkILfwOrNnAiDZFHN4kevYvsEuRgC
P3eL6+C4Kk0POUyzdon9yOag83aPE0SBIp6Tbl5uhxCXNrAzwd6qOv31k+v1GbMN
x8qitKBEkE/BG254diNalDp8/VGx4YHhgxcKOYhRy5PUU2SoVlpfTz5L8uenWN/Y
jOJiXoxosdnKuHz3AgMBAAGjgaIwgZ8wCQYDVR0TBAIwADAvBgwrBgEEAZIICQIA
AQEEHwwdUHVscCBQcm9kdWN0aW9uIE15UmVwbyB4ODZfNjQwJQYMKwYBBAGSCAkC
AAECBBUME3B1bHAtcHJvZC1teXJlcG8tNjQwOgYMKwYBBAGSCAkCAAEGBCoMKHJl
cG9zL3B1bHAvcHVscC8kcmVsZWFzZXZlci8kYmFzZWFyY2gvb3MwDQYJKoZIhvcN
AQEFBQADggIBAIl+MAl1cuxOhHWAf1TMEvkk+bJ1KVQXpanFQlgosTy3+WupGV6n
HB9799mMC5i0k1IpfAaB9PD4BM72V64Pgq25mAANKcQvuTUSFryLERx7MwJoyABn
W1IQGYBGOT1TaNxSXGq5K3oqo5Mt5sEt39sMNenOJaR+sfqhHRsDRKJB/qgTcpqr
PLJIuv5j2VmWDPwyEZnWrLL6g3LBWHGxWECajJdscVbugdBuF4AgEFDPeLGrAb5i
uacJAR7SXA8AqV95CaxXuMv/xILTT4IZnVBkf84a9Fz6NdS2kYaw6ULTqZ8uIoAY
M2pnWkYOWoY7aOV5s8xrp8xaWLGm0cp5Kf3hv27anqyHW/tZ7pN21Tihgu6Wzuhm
KoUG+HEddLu7WqKAic6lNf0pZCKBoJTeACGTfHyu5rWX6GRcq7URojoHN9XYFp5E
RScWmtvyVn3yDyOr834mJGTgZlOpbEegkxv2e2BDWB6ZcsRvmJiN9y53ApiRmOYc
Oy+y9guwfHap61R/Z/k+Y1AH6CchNmm8NuC3zSWqImOYRnzhn80dxSeGjyOJKpCY
WVwETFWZTf5M/Z1eXn/Pk43VWAJmSTZXL5ri7MeHr3bOja5OczJ4cJHIa62159C2
252LiTSm5DTYby8TH8890nZ/Rfek34kcD5eXYROq6FuQNfwLrEBaunnX
-----END CERTIFICATE-----
'''

WILDCARD_CLIENT_KEY = '''
-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----
'''

# Grants access to:
# repos/pulp/pulp/$releasever/$basearch/os
FULL_WILDCARD_CLIENT = '\n'.join((WILDCARD_CLIENT_KEY, WILDCARD_CLIENT))

ANYKEY2 = '''
-----BEGIN RSA PRIVATE KEY-----
MIIBOQIBAAJBALHtPMOOqLs1oDwjD2A0jt5sLYhreJre0USH/ZnuIQvDq6sb6msF
ud0/5mRSRolY61TRorKvHQ3OawtZS3C4R0MCAwEAAQJAHo5mjBMY6SW5gfpnbpc4
HfyoCTCjwr0XZVSRefkKVdGYLYMm1LdeRjSTOVLqNVB3QQbEjEKCVCZQ0xvWTwlk
CQIhAOp40LB8SbFTFA/+rIh6jkhjnsU+tqGawMZZDTR19muVAiEAwkNYbwAs/Mo/
o5YGGk7fdVlfUb/2PWKGg2MyPc8R8XcCIB/G8/GXRp2DtupcB6IPig0Bg1kUIMhS
IuI+221Kt3TpAiA1j0XRjNXaeJSlMJbMKBTaEOMD8g4dDI4TqYTPn8jNrwIgEQ8j
nctWK1z+N+TUw1s9urJD99DNKpnXpcYzz3SU6r0=
-----END RSA PRIVATE KEY-----
'''

ANYCERT2 = '''
-----BEGIN CERTIFICATE-----
MIIDezCCAWMCCQCILWwuj/w7QDANBgkqhkiG9w0BAQUFADBiMQswCQYDVQQGEwJV
UzELMAkGA1UECAwCTkMxEDAOBgNVBAcMB1JhbGVpZ2gxEDAOBgNVBAoMB3Rlc3Qt
Y2ExEDAOBgNVBAsMB3Rlc3QtY2ExEDAOBgNVBAMMB3Rlc3QtY2EwHhcNMTExMDI0
MTg0MTUxWhcNMzkwMzExMTg0MTUxWjBlMQswCQYDVQQGEwJVUzELMAkGA1UECAwC
TkMxEDAOBgNVBAcMB1JhbGVpZ2gxETAPBgNVBAoMCHRlc3QtYW55MREwDwYDVQQL
DAh0ZXN0LWFueTERMA8GA1UEAwwIdGVzdC1hbnkwXDANBgkqhkiG9w0BAQEFAANL
ADBIAkEAse08w46ouzWgPCMPYDSO3mwtiGt4mt7RRIf9me4hC8OrqxvqawW53T/m
ZFJGiVjrVNGisq8dDc5rC1lLcLhHQwIDAQABMA0GCSqGSIb3DQEBBQUAA4ICAQBz
ofMtaNgR+6gYJhgBU3kFhW3SNS+6b1BCDrJZ6oLfae9bIfC/ri/phpQGEGjZOcoY
zyYRy7xAruW6A5p6QMkJ4inFUeiWeok6gdbmmIkgO2Y0xGnYfSq1eLNBUQ7bpjFU
pAvwpG+ByYYA+yJywC53gzcG14BpzAMCGpp6xXIvW9JBpkYhxcQOfwVw4qSPwRlz
2SJ4L/616MLXuHfiJneYZITtXDQKqePc8f1rqP5l0Ja1/5oatAggBwfBoj4HBSqY
khTByxSoThv4yPAJ9BwC5R3j7yLmtCpgbp3lWVn+mtwJ0u+roznvGLnI346bnU3Q
wMGUhyoSGTYdpi44YK2HSHRZgwSzCClkVQHES64jyUIfBjgtWKZaWY9/JYCnFNFY
25uPrkg6em2WGRJgwUnotv/sdMbpJfMSkgYwSvrgEQJxKXNE8aXSylXjBaDq0+4f
ex3AFJ35OYcRkpS3+RRFPifB8NX/YpqQwBgnhwXfntJPxTDE+4Ad9IQTR3Jkr2qT
yHBxNafX9/D7PxcuY8UR0ZRSLaUn9UG6G6UcWZa8HdqMcXI5YecZUC8Pi5D6rVaZ
tvkBDkSXz3GUeyK11pQC9xYWz7Pyy5+5NktBQ8chDZX0ENWHbGqR9xgHIZXJd0Ks
4Y0Tl5d9N8mMNOpaDsn9Lr+E72NmK3A7Phl8jQow3g==
-----END CERTIFICATE-----
'''

# Entitlements for:
#  - repos/pulp/pulp/fedora-13/$basearch/
#  - repos/pulp/pulp/fedora-14/$basearch/
#
# Signed with VALID_CA2
ENDS_WITH_VARIABLE_CLIENT = """
-----BEGIN CERTIFICATE-----
MIIFYjCCA0qgAwIBAgIBZDANBgkqhkiG9w0BAQUFADBiMQswCQYDVQQGEwJVUzEL
MAkGA1UECAwCTkMxEDAOBgNVBAcMB1JhbGVpZ2gxEDAOBgNVBAoMB3Rlc3QtY2Ex
EDAOBgNVBAsMB3Rlc3QtY2ExEDAOBgNVBAMMB3Rlc3QtY2EwHhcNMTIwMjIwMjIy
NTU1WhcNMTQxMTE2MjIyNTU1WjBoMQswCQYDVQQGEwJVUzELMAkGA1UECAwCTkMx
EDAOBgNVBAcMB1JhbGVpZ2gxEjAQBgNVBAoMCVB1bHAgVGVzdDESMBAGA1UECwwJ
UHVscCBUZXN0MRIwEAYDVQQDDAlwdWxwLXRlc3QwggEiMA0GCSqGSIb3DQEBAQUA
A4IBDwAwggEKAoIBAQDEZI7HgKMOnh/yIFm+cw+O0EQNDaPYzahi+qJ0UmGjIwky
nLt09Zz2wU1ZcUkMPXGodmp16CWhWcyHHO3NETxjKSUd8FXv9LDgTE3g9AhR8HYY
p9paO+QDC5XXP+6np7jE/W8WkCmdzA0W2pc/hEiFxWT8fzstnKeb1sKtzhEAHEcD
IXWGX0Y6CmfsUPpB4XSQ+AWmpHnvL8j9qN0/sS2NmTgQS7bocqQfekKwhEqMy/Lt
mEtw6m6tV9IHtHrm/5ZPkDA467ReZEwuOY4CRMpHURYYCs5zuSAMJx7eTb2dcEMR
f5QL7epQRubfV7hVdXEDi4hOwc5JQ4zl/ezsvScTAgMBAAGjggEbMIIBFzAJBgNV
HRMEAjAAMCsGDCsGAQQBkggJAgABAQQbDBlQdWxwIFByb2R1Y3Rpb24gRmVkb3Jh
IDEzMB8GDCsGAQQBkggJAgABAgQPDA1wdWxwLXByb2QtZjEzMDYGDCsGAQQBkggJ
AgABBgQmDCRyZXBvcy9wdWxwL3B1bHAvZmVkb3JhLTEzLyRiYXNlYXJjaC8wKwYM
KwYBBAGSCAkCAwEBBBsMGVB1bHAgUHJvZHVjdGlvbiBGZWRvcmEgMTQwHwYMKwYB
BAGSCAkCAwECBA8MDXB1bHAtcHJvZC1mMTQwNgYMKwYBBAGSCAkCAwEGBCYMJHJl
cG9zL3B1bHAvcHVscC9mZWRvcmEtMTQvJGJhc2VhcmNoLzANBgkqhkiG9w0BAQUF
AAOCAgEAtnDZoKeXtCw/hJAhcUNNoN6VL+B3ShtY3qq0hxNl7lgTPU2908gHVFt5
PvoDVKIXTdLEbU4mT9Hfnh1zMGOE2IcqviGZ2LfLdtZnmY/khS2KwpH5MzG1K9+L
eB9F8zEKVa/nnIxw8StsH8z5ejEyOb8z/cOy+lRuHTJZkuiM1sVMOU95ixkJqfJb
WDZCkzdM+bFfYU9wDM58ONZEn9WsynrswQeXqi6uh6K26DxNMqRqkcHCiEi66H1X
FiExl7TNxpNMfHS0XY6ZTuO2bI0XgTmFbAHTd3XCpNPhNblpHrHhx+KXrDqHgZBR
D8MgbvtnhGU/ioUQuwP/h2wOYX7jmOEWWaPishrgEsS0KAvTorDp9esHharcXNnU
ibYPWp0/4gN/RJAjIRf5DWmcXKRibPfg6qXlADG2MnVp7oZVNqan3W2SLseUMNYS
ph5EPvhUxLMxDd5gncX1MDBENDX6mzbhpd1+CPB44n+nCpjR0rZkjOG+Q3G1m77V
09j4IRuYCEtp0NhgQHXV8L0BDofIj8egtE7MmyPCrKIlDTpHZ5cfduzgt0hVpmOt
zTrt2Dm0DZ9LwFANfRpkpI0ZNKg1/pKlxQOijR/EN2imsLvu/fdfR6dov7PBxfoX
PQvdFGUaYghwNKmFU3ij98jodzfd4x3CnHXgu+Bh2PO425Ww4/8=
-----END CERTIFICATE-----
"""

ENDS_WITH_VARIABLE_CLIENT_KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAxGSOx4CjDp4f8iBZvnMPjtBEDQ2j2M2oYvqidFJhoyMJMpy7
dPWc9sFNWXFJDD1xqHZqdegloVnMhxztzRE8YyklHfBV7/Sw4ExN4PQIUfB2GKfa
WjvkAwuV1z/up6e4xP1vFpApncwNFtqXP4RIhcVk/H87LZynm9bCrc4RABxHAyF1
hl9GOgpn7FD6QeF0kPgFpqR57y/I/ajdP7EtjZk4EEu26HKkH3pCsIRKjMvy7ZhL
cOpurVfSB7R65v+WT5AwOOu0XmRMLjmOAkTKR1EWGArOc7kgDCce3k29nXBDEX+U
C+3qUEbm31e4VXVxA4uITsHOSUOM5f3s7L0nEwIDAQABAoIBAQCxBnt09U0FZh8h
n2uFsi15690Lbxob2PVJkuZQt9lutawaxRBsEuETw5Y3Y1gXAmOrGGJKOaGB2XH0
8GyiBkFKmNHuNK8iBoxRAjbI6O9+/KNXAiZeY9HZtN2yEtzKnvJ8Dn3N9tCsfjvm
N89R36mHezDWMNFlAepLHMCK7k6Aq2XfMSgHJMmHYv2bBdcnbPidl3kr8Iq3FLL2
0qoiou+ihvKEj4SAguQNuR8w5oXKc5I3EdmXGGJ0WlZM2Oqg7qL85KhQTg3WEeUj
XB4cLC4WoV0ukvUBuaCFCLdqOLmHk2NB3b4DEYlEIsz6XiE3Nt7cBO2HBPa/nTFl
qAvXxQchAoGBAPpY1S1SMHEWH2U/WH57jF+Yh0yKPPxJ6UouG+zzwvtm0pfg7Lkn
CMDxcTTyMpF+HjU5cbJJrVO/S1UBnWfxFdbsWFcw2JURqXj4FO4J5OcVHrQEA6KY
9HBdPV6roTYVIUeKZb6TxIC85b/Xkcb3AHYtlDg3ygOjFKD6NUVNHIebAoGBAMjT
1bylHJXeqDEG+N9sa1suH7nMVsB2PdhsArP3zZAoOIP3lLAdlQefTyhpeDgYbFqD
wxjeFHDuJjxIvB17rPCKa8Rh4a0GBlhKEDLm+EM3H0FyZ0Yc53dckgDOnJmyh9f+
8fc7nYqXEA7sD0keE9ANGS+SLV9h9v9A7og7bGHpAoGAU/VU0RU+T77GmrMK36hZ
pHnH7mByIX48MfeSv/3kR2HtgKgbW+D+a47Nk58iXG76fIkeW1egPHTsM78N5h0R
YPn0ipFEIYJB3uL8SfShguovWNn7yh0X5VMv0L8omrWtaou8oZR3E2HGf3cxWZPe
4MNacRwssNmRgodHNE2vIr8CgYABp50vPL0LjxYbsU8DqEUKL0sboM9mLpM74Uf0
a6pJ8crla3jSKqw7r9hbIONYsvrRlBxbbBkHBS9Td9X0+Dvoj3tr1tKhNld/Cr0v
bi/FfgLH60Vmkn5lwWGCmDE6IvpzkSo1O0yFA9GiDdfiZlkLcdAvUCkHjCsY11Qf
0z2FYQKBgQDCbtiEMMHJGICwEX2eNiIfO4vMg1qgzYezJvDej/0UnqnQjbr4OSHf
0mkVJrA0vycI+lP94eEcAjhFZFjCKgflZL9z5GLPv+vANbzOHyIw+BLzX3SybBeW
NgH6CEPkQzXt83c+B8nECNWxheP1UkerWfe/gmwQmc0Ntt4JvKeOuw==
-----END RSA PRIVATE KEY-----
"""
