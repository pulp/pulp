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

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pulp.repo_auth.oid_validation as oid_validation
from pulp.repo_auth.oid_validation import OidValidator
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

    # See https://fedorahosted.org/pulp/wiki/RepoAuth for more information on scenarios

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
-----BEGIN CERTIFICATE-----
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
I9bmz1dqBo2/e4UnBko=
-----END CERTIFICATE-----
'''

# Entitlements for:
#  - repos/pulp/pulp/fedora-13/x86_64/
#  - repos/pulp/pulp/fedora-14/x86_64/
FULL_CLIENT_CERT = '''
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
-----BEGIN CERTIFICATE-----
MIIGXTCCBEWgAwIBAgIBAjANBgkqhkiG9w0BAQUFADBlMQswCQYDVQQGEwJVUzEL
MAkGA1UECAwCTkoxEjAQBgNVBAcMCU1pY2tsZXRvbjEQMA4GA1UECgwHUmVkIEhh
dDEPMA0GA1UECwwGUHVscCAxMRIwEAYDVQQDDAlwdWxwLWNhLTEwHhcNMTEwMzI4
MTYwNzAxWhcNMTIwMzI3MTYwNzAxWjBmMQswCQYDVQQGEwJVUzELMAkGA1UECAwC
TkoxEjAQBgNVBAcMCU1pY2tsZXRvbjEQMA4GA1UECgwHUmVkIEhhdDENMAsGA1UE
CwwEUHVscDEVMBMGA1UEAwwMY2xpZW50MS1mdWxsMIICIjANBgkqhkiG9w0BAQEF
AAOCAg8AMIICCgKCAgEAy4kK8GgojbDq2HnFWjSwynrJHLppuiZrMZDzFymaLrUw
U7svP0Xtwgf3VYwHQGqL70DY/1mcuaBmW9sBVUiRh5p6eSTfMbGqHoXvB+utw9tQ
VgmATNaj7r+hj/1ITyWJxvIRpD7rh2LlkwhtbMav0ftAfWvXafqbbkMpHGA1uQ9b
YxJJm1XCNzLI2gKQROm04cAIsJv/zAihVRmjtpm6HFwyY0tj06/pbuKf0J/UvOz6
+2LOuhXiZz2z9c3oQM1KmlyQJstgZuPfydxQCE+tWYVbeW3JkqlqlKc++TK+jy+9
Ue9nhf6kCQZhWTGNyhCjM9bMSzgtK1L6dveKekEwXYja+c+Vu/IiEP2vKE1H5Bgz
lsfh4Dyr0bXdVl5YsBIPRcv6ptvJps0Ko2P1cFPsB1vchZD981LvBI6DLFpKWSVS
b9kpbiWRpX3MGhf2ZObZ+IaYndbw7rAn5fhGKumn3vSNFLhZnvoCP5hrrhYygjoF
fS83H7lH2jdxJ3nO4iHfbk/BT3EsbLodIcOgR3CQCH5UedIwpXUWqV344b0w2Xh5
88dnAMHgpu8i9JUP4qy2q1XtZYXqKO/p5VwuE218eY5S4LKpEwn/xHTBAjLgwYkE
bOa9lCEf8N7vBNMKPyAib1hBb9bc5k0bSzkot45rjVbdELMbhg3uPkrt87SPVIcC
AwEAAaOCARUwggERMAkGA1UdEwQCMAAwKwYMKwYBBAGSCAkCAAEBBBsMGVB1bHAg
UHJvZHVjdGlvbiBGZWRvcmEgMTQwHwYMKwYBBAGSCAkCAAECBA8MDXB1bHAtcHJv
ZC1mMTQwMwYMKwYBBAGSCAkCAAEGBCMMIXJlcG9zL3B1bHAvcHVscC9mZWRvcmEt
MTQveDg2XzY0LzArBgwrBgEEAZIICQIBAQEEGwwZUHVscCBQcm9kdWN0aW9uIEZl
ZG9yYSAxMzAfBgwrBgEEAZIICQIBAQIEDwwNcHVscC1wcm9kLWYxMzAzBgwrBgEE
AZIICQIBAQYEIwwhcmVwb3MvcHVscC9wdWxwL2ZlZG9yYS0xMy94ODZfNjQvMA0G
CSqGSIb3DQEBBQUAA4ICAQBF2erUvu2v/10QBLuGr2ItMt9D0pWoUEAgJMSMPNRc
TbfSulsNEIVbVEIoBUxvOD/Y4uxiGPhXAyiDBxWpRyeScKzsLpJoGVi4feBV+SvJ
ykk5ocx1Ou+57nYalfMg8uRBpFYik7/X8m30Bsb63fnqcweE2XjVjebjG43iG78g
jyl+uEzcYeGo1WCymhT66OH3WT46aDlDsQOpcCC/VMcqj/jyBNlo2WjlKUvnvCSX
k93bBCi/cQ7fcdAlyFDgBTI1GIu2F4Zl0WBuQUiYDSo49uvUpwiufWteyONMwXj5
2qbQuRiyiQ59fkWE2MQgtoOMyT/gPsDfbwnC7UphEAA0qT4iNWmXah+bzRwUA/Ic
YVlPokRr6FQAH4edffAw1FF2B/Hd0DrFqG3KvBBYssK3tCK2iMquK6m34a7ja059
khc02MWDvkF6O/WCaL+dOOY0/QMGoJN+o/GrMYJwjsPblUQtEihXJVrE5I2xT8FA
TlISug1aV2N3kfE89VqnLciKHg3F2Kq95Syaf7NHtKtxLWaFZr0VfvvpCVL89UgU
edV07LlKUOOtS4yjknwfJvBADP3DVN+s1zw2orkQq2azf0+OhnxjWg+KibKroHi6
5smAmdaRMexu1zJyn9r4Jreod+znjQtnw1y2vE5BE1fjB66HHY6g0DhuSDOOGj1L
lQ==
-----END CERTIFICATE-----
'''

VALID_CA = '''
-----BEGIN CERTIFICATE-----
MIIFnTCCA4WgAwIBAgIJAMH9nQr2GQwCMA0GCSqGSIb3DQEBBQUAMGUxCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQK
DAdSZWQgSGF0MQ8wDQYDVQQLDAZQdWxwIDExEjAQBgNVBAMMCXB1bHAtY2EtMTAe
Fw0xMTAzMjUxOTUwNTlaFw0xMjAzMjQxOTUwNTlaMGUxCzAJBgNVBAYTAlVTMQsw
CQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQKDAdSZWQgSGF0
MQ8wDQYDVQQLDAZQdWxwIDExEjAQBgNVBAMMCXB1bHAtY2EtMTCCAiIwDQYJKoZI
hvcNAQEBBQADggIPADCCAgoCggIBANwv8xjqslOq+651JLjoKrIVx6H/wcpYlvWH
1Bhy+H0THOoNlfBXKt9WHsjx5DzDBokEUC6MwaG673vrMOepLjAbLz1h0weEtj0Y
xlrGY4vXwhB0hDrIHqSf+oGcYkJur1M5Mz76Ucfm7hNn/kYC8JznLR1X/GhBPoeZ
XHzSBn070BMBk68Y46DVfQJKQfnlAJaoEetO6++w1MFZGzZS33AEW3hDsHQ75OoX
IpM7A17rfO5HzdBaHHHhMwcuG8hlJxAroXiCLa3CziGo0seAWPkCSDX6Eo7/GhDR
ewP3+PH4r0oFjbJj60onR5ONznHbVUcMHhLWlQzo0vnwrr3sRt49KOjsBD6CKVlo
LHo1b6khcuxBcAM2uyC45HhTIZIjBX79E3OEMhnDMHct3RLj9dP2ww+foz2+5iay
dPvCdLGAQ0UD3unaipHiWU551EEUTpstyGUO9A2uN8+R67SHcTvkxbgvTJZ9ytpV
RotZ6e41SjDBEj6Y+cEQsDciU0xk6WN3aII01F2J+lREB529wlEi582SP4UMErQH
NF4VEiHFCKn+MlkJ2BbYZA5V8SrbtNq2Rf0jXKUlcc9rqKCHmBDuUDYQoddwcgNe
d+ecwjbUWjBaB1CG3NEb6Jro7JjtFgE5D6FkChkb94qpmcLjViEKP+TvZYhqhLBT
AczTQe1dAgMBAAGjUDBOMB0GA1UdDgQWBBSE7cYaW9SXLeJOP3fyi0knZo4WLjAf
BgNVHSMEGDAWgBSE7cYaW9SXLeJOP3fyi0knZo4WLjAMBgNVHRMEBTADAQH/MA0G
CSqGSIb3DQEBBQUAA4ICAQDLNtVSUZfFbaqMF78MwWyrKqhDDo6g1DHGTqOYxK+v
jBkNPIdOFDEJzxVcRFCs2puKH4lHU+CfJo4vDbQ93ovXBWVACjS/pX0FJQ1e10oB
Ky3Lo6fuIjecO6Y2eoTWNadJkcjyrhcDKDOHaZb5BBFS3Lx8F37U9TGsy47jNS+x
l0wfCBeydNzEY4pYXPxMK/3TY48WM8pSn5ML/rrD3Em1Omt86pYW98DNB1Ibqc1Y
614qYPzStEYxXcg5fkIJBliVZmruKutGc3EzTQwa9E/UKN3zFfWfOYSl6Hgo7UKS
gAYHhQm6/6jREGgSFDG9bQa4qEMNLrYc1cWYm9daKoAhVfJ3Cm8GYdyeD2mDh/n6
p3k8fqdOs5hKYCgusUDgdZ4B5nC7H05vVnCXVyfwN5zRb3NxgjkPlgClOdvlsrTT
dFLor0h7zsSC7tV+0LVItwqWl6b6v6AutRJz1Q0H7NPWw96yQodX2Tl/1IOtM2j1
qkbOzF1i1H/SQ22dHLT2ayT+Zz84okUtTN417+Rn2tvUTmDMbPft28LmzguItw1e
ySWfIQ51GrBhqUH8qI1UfCduu/QA/sHT0pmKmxIzchZH9/kCyZRFPG7+OzDyj/Dx
3xYZYYqU3eMSvj72/hifSZtipT1qWkxpAdSz9c9ZGZXeiZUl/23UyeGq1qp7wU+k
Hg==
-----END CERTIFICATE-----
'''

INVALID_CA = '''
-----BEGIN CERTIFICATE-----
MIIFnTCCA4WgAwIBAgIJAII71LRLCAczMA0GCSqGSIb3DQEBBQUAMGUxCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQK
DAdSZWQgSGF0MQ8wDQYDVQQLDAZQdWxwIDIxEjAQBgNVBAMMCXB1bHAtY2EtMjAe
Fw0xMTAzMjUyMDA0MTBaFw0xMjAzMjQyMDA0MTBaMGUxCzAJBgNVBAYTAlVTMQsw
CQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQKDAdSZWQgSGF0
MQ8wDQYDVQQLDAZQdWxwIDIxEjAQBgNVBAMMCXB1bHAtY2EtMjCCAiIwDQYJKoZI
hvcNAQEBBQADggIPADCCAgoCggIBALIZrAAZFxKqzpMXiIwClv/o1tyFn6hnUhEX
HXaCHoY5QZZ695UXz9b0dxNKaMgfEq9fjfdP3f8A1yg9lTIyiG4BAPpSla/RT/B6
fBwLF2WBvCbPJB7w5+ZLCHkDIOd6swBQUEHXGOIEk1IUByEndlksHzzUpVL8BDq4
gMfDCmsV5SsfcQN8ophgXN6fOPHtluOmfIjxoCq69aB0NjjDzYbW9Vo/2VLeNbdv
XEfZRBgJv/VpSAQF8POB3yHUw95GN5OjECXhMBQ2mlyyNksVSFIn2yOBwr7tejVA
61pjZio1CMN5JLc63DZQkBNEtGknG6qmcVhZUjhINsK5R1S/Mh3oyT9/c1W+yPii
oJOe7PEemlWSwt4ufFnXbRMbUDx9g0ud6nUxnXPA9RugkfkXvsXKct4ql1WI64jL
3sDUNN65aj8W8LG+WOEYuXvuyXkFl/lMT9wzLG9Y85xB6S1wnggS/4zVikptHEFK
KjLOlCWYPQNmbjUiekkRk/qnAixTqLcNXssVj4GlW9ElZeu4mNidk/lXoeVzyIBJ
710OjUH7EuMe87gPf3q0x/Cm6E98O6b9Zqhm6/4nQSrd1YT5kqRfCWMyKP8bdSpU
HAT6Zx3b1df4mdZZ6JW7MF5cXHaGxZzdA7WVpq6YAg7JJxBt9B2KOQyj1kXOeWuD
RU1qIJCtAgMBAAGjUDBOMB0GA1UdDgQWBBT2RGJP7ERHn5q5rR7gOsfybW5zMDAf
BgNVHSMEGDAWgBT2RGJP7ERHn5q5rR7gOsfybW5zMDAMBgNVHRMEBTADAQH/MA0G
CSqGSIb3DQEBBQUAA4ICAQBI2Yi0q2S2giGy/banh3Ab3Qg1XirkGa3HmA2JF7XV
dcsPjzDwKd3DEua76gZ94w+drEve0z95YPC02jiK2/9EOyoIS+Sc3ro698mUuUuY
A0vxAQJEoQNlCtNs7St60L98wWp64oTiTPTBjYBoQsBYul9Omh/qkmMqz/L/t47T
nc3AcVzrDwesNlyWUMPg1SajXth4ux6+7/GiWaE8QRZiX6LjN6362dN8J7P39iBj
Ftw1duPZTYg5gkmuYjy+CfSvSyzq/TKV5JYVWijpAzAM9iyoBQFLEfzA8Vb+C+kk
DTKhBObJF1aGxJHFkIqN2XnKaBAQYzR3y7duUJS7OmufSVwsJgzT1jUCZ/qFLFlW
TSiSdWGGR2NzsMoO4mCLBFpHe2PENFy//US1OQERNBHZKFx3t8YyLh8tzda5goXM
4K+FIH1+WeoibKr+UnQC4CU3Ujbf3/Ut7+MDu5A76djkPjgIbJChe3YoExBzJck3
DAK56kpnnuqwj0EyAqpsEiF4CAcpBwLP7LVc68XGfzIzRaRJOlerEscFR2USmW+c
+ITpNVXEGdZgdBjIIq/n+59JqEHnKinRaQMZBNppD6WZ6NVelcb4094kc1H1Qpkt
f/LU796X0sQbbbpuKab4CNNYaj7ig5wnbC5ONYmYTebcOML+H9b/iOomNCPDmLpj
tA==
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
