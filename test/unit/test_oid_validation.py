#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
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
import shutil
import sys
import os
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.repo_auth import oid_validation, repo_cert_utils
from pulp.server.api.repo import RepoApi
from pulp.server.api.auth import AuthApi
import testutil

# -- constants ------------------------------------------------------------------

CERT_TEST_DIR = '/tmp/test_oid_validation/'

# -- mocks ----------------------------------------------------------------------

class MockRequest:

    def __init__(self, client_cert_pem, uri):
        self.client_cert_pem = client_cert_pem
        self.uri = uri

    def ssl_var_lookup(self, lookup_var_name):
        return self.client_cert_pem

    def log_error(self, message):
        pass

# -- test cases -----------------------------------------------------------------

class TestOidValidation(unittest.TestCase):

    def clean(self):
        if os.path.exists(CERT_TEST_DIR):
            shutil.rmtree(CERT_TEST_DIR)

        protected_repo_listings_file = self.config.get('repos', 'protected_repo_listing_file')
        if os.path.exists(protected_repo_listings_file):
            os.remove(protected_repo_listings_file)

        self.repo_api.clean()

    def setUp(self):

        # Test configuration setup
        override_file = os.path.abspath(os.path.dirname(__file__)) + '/../common/test-override-repoauth.conf'
        self.config = testutil.load_test_config()

        repo_cert_utils.CONFIG_FILENAME = override_file
        oid_validation.PROTECTED_REPOS_FILENAME = self.config.get('repos', 'protected_repo_listing_file')

        self.repo_api = RepoApi()
        self.auth_api = AuthApi()

        self.clean()

    def tearDown(self):
        self.clean()

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

        repo_x_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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

        repo_x_bundle = {'ca' : INVALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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

        repo_y_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch', consumer_cert_data=repo_y_bundle,
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest(LIMITED_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest(LIMITED_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')
        
        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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
        global_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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
        global_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest(LIMITED_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest(LIMITED_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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
        global_bundle = {'ca' : INVALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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
        global_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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
        global_bundle = {'ca' : INVALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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
        global_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca' : INVALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest(FULL_CLIENT_CERT, 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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

        repo_x_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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
        global_bundle = {'ca' : INVALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

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
        global_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca' : VALID_CA, 'cert' : 'foo', 'key' : 'bar'}
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='yum:http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = MockRequest('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = MockRequest('', 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x)
        response_y = oid_validation.authenticate(request_y)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(not response_y)


# -- test data ---------------------------------------------------------------------

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