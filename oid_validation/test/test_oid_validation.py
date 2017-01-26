#
#
# This test is currently disabled. It needs to be changed to not use server
# API classes and instead set up the auth directly, however I just don't have
# the time during the git refactor to do it now.
# jdob, June 12, 2012
#
#

from ConfigParser import SafeConfigParser, NoOptionError
import shutil
import os
import unittest
import urlparse

from M2Crypto import X509
import mock

import pulp.oid_validation.oid_validation as oid_validation
from pulp.repoauth.repo_cert_utils import RepoCertUtils

DATA_DIR = os.path.abspath(os.path.dirname(__file__)) + '/data'
CERT_TEST_DIR = '/tmp/test_oid_validation/'
CONFIG_FILENAME = os.path.join(DATA_DIR, 'test-override-repoauth.conf')


def load_data(basename):
    # given a basename, read the file with that name in DATA_DIR and return its contents
    with open(os.path.join(DATA_DIR, basename)) as f:
        return f.read()


# "valid" CA, along with cert signed by that CA along with its key
VALID_CA = load_data('valid_ca.crt')
CERT = load_data('cert.crt')
KEY = load_data('cert.key')

# "other" CA, along with cert signed by that CA along with its key
OTHER_CA = load_data('other_ca.crt')
OTHER_CA_KEY = load_data('other_ca.key')

OTHER_CERT = load_data('other_cert.crt')
OTHER_CERT_KEY = load_data('other_cert.key')

# Entitlements for:
# - repos/pulp/pulp/fedora-14/x86_64/
E_LIMITED = '\n'.join((load_data('e_limited.crt'), load_data('e_limited.key')))

# Entitlements for:
#  - repos/pulp/pulp/fedora-13/x86_64/
#  - repos/pulp/pulp/fedora-14/x86_64/
E_FULL = '\n'.join((load_data('e_full.crt'), load_data('e_full.key')))

# Entitlements for:
# - repos/pulp/pulp/$releasever/$basearch/os
E_WILDCARD = '\n'.join((load_data('e_wildcard.crt'), load_data('e_wildcard.key')))

# Entitlements for:
#  - repos/pulp/pulp/fedora-13/$basearch/
#  - repos/pulp/pulp/fedora-14/$basearch/
E_VARIABLE_CERT = load_data('e_variable.crt')
E_VARIABLE_KEY = load_data('e_variable.key')


def mock_environ(client_cert_pem, uri):
    environ = {}
    environ["mod_ssl.var_lookup"] = lambda *args: client_cert_pem
    # Set REQUEST_URI the same way that it will be set via mod_wsgi
    path = urlparse.urlparse(uri)[2]
    environ["REQUEST_URI"] = path

    class Errors:
        def write(self, *args, **kwargs):
            pass

    environ["wsgi.errors"] = mock.Mock(spec=file)
    return environ


class TestOidValidation(unittest.TestCase):
    def clean(self):
        if os.path.exists(CERT_TEST_DIR):
            shutil.rmtree(CERT_TEST_DIR)

        protected_repo_listings_file = self.config.get('repos', 'protected_repo_listing_file')
        if os.path.exists(protected_repo_listings_file):
            os.remove(protected_repo_listings_file)

    def setUp(self):
        self.config = SafeConfigParser()
        self.config.read(CONFIG_FILENAME)

    def print_debug(self):
        valid_ca = X509.load_cert_string(VALID_CA)
        other_ca = X509.load_cert_string(OTHER_CA)
        print "--Reference Values--"
        print "OTHER_CA: %s %s" % (other_ca.get_subject(), other_ca.get_subject().as_hash())
        print "VALID_CA: %s %s" % (valid_ca.get_subject(), valid_ca.get_subject().as_hash())

    # See https://fedorahosted.org/pulp/wiki/RepoAuth for more information on scenarios
    def simple_m2crypto_verify(self, cert_pem, ca_pem):
        cert = X509.load_cert_string(cert_pem)
        ca_cert = X509.load_cert_string(ca_pem)
        return cert.verify(ca_cert.get_pubkey())

    @mock.patch('pulp.oid_validation.oid_validation.OidValidator._check_extensions',
                return_value=True)
    @mock.patch('pulp.oid_validation.oid_validation.RepoCertUtils.validate_certificate_pem')
    @mock.patch(
        'pulp.repoauth.protected_repo_utils.ProtectedRepoUtils.read_protected_repo_listings')
    @mock.patch('pulp.repoauth.repo_cert_utils.RepoCertUtils.read_consumer_cert_bundle')
    def test_is_valid_verify_ssl_false(self, mock_read_bundle, mock_read_listings,
                                       validate_certificate_pem, _check_extensions):
        """
        Test is_valid when verify_ssl is false.
        """
        self.config.set('main', 'verify_ssl', 'false')
        repo_x_bundle = {'ca': OTHER_CA, 'key': KEY, 'cert': CERT, }
        mock_read_listings.return_value = {'/pulp/pulp/fedora-14/x86_64': 'repo-x'}
        mock_read_bundle.return_value = repo_x_bundle
        request_x = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')

        valid = oid_validation.authenticate(request_x, config=self.config)

        # Make sure we didn't call into the cert validation code
        self.assertEqual(validate_certificate_pem.call_count, 0)
        # It should be valid because we mocked _check_extensions to return True
        self.assertEqual(valid, True)

    @mock.patch('pulp.oid_validation.oid_validation.OidValidator._check_extensions')
    @mock.patch('pulp.oid_validation.oid_validation.RepoCertUtils.validate_certificate_pem',
                return_value=False)
    @mock.patch(
        'pulp.repoauth.protected_repo_utils.ProtectedRepoUtils.read_protected_repo_listings')
    @mock.patch('pulp.repoauth.repo_cert_utils.RepoCertUtils.read_consumer_cert_bundle')
    def test_is_valid_verify_ssl_true(self, mock_read_bundle, mock_read_listings,
                                      validate_certificate_pem, _check_extensions):
        """
        Test is_valid when verify_ssl is true.
        """
        self.config.set('main', 'verify_ssl', 'true')
        repo_x_bundle = {'ca': OTHER_CA, 'key': KEY, 'cert': CERT, }
        mock_read_listings.return_value = {'/pulp/pulp/fedora-14/x86_64': 'repo-x'}
        mock_read_bundle.return_value = repo_x_bundle
        request_x = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')

        valid = oid_validation.authenticate(request_x, config=self.config)

        # Make sure we didn't call into the cert validation code
        self.assertEqual(validate_certificate_pem.call_count, 1)
        # It should be other because we mocked validate_certificate_pem to return False
        self.assertEqual(valid, False)
        # _check_extensions shouldn't have been called
        self.assertEqual(_check_extensions.call_count, 0)

    @mock.patch('pulp.oid_validation.oid_validation.OidValidator._check_extensions')
    @mock.patch('pulp.oid_validation.oid_validation.RepoCertUtils.validate_certificate_pem',
                return_value=False)
    @mock.patch(
        'pulp.repoauth.protected_repo_utils.ProtectedRepoUtils.read_protected_repo_listings')
    @mock.patch('pulp.repoauth.repo_cert_utils.RepoCertUtils.read_consumer_cert_bundle')
    def test_is_valid_verify_ssl_undefined(self, mock_read_bundle, mock_read_listings,
                                           validate_certificate_pem, _check_extensions):
        """
        Test is_valid when verify_ssl is undefined.
        """
        self.config.remove_option('main', 'verify_ssl')
        repo_x_bundle = {'ca': OTHER_CA, 'key': KEY, 'cert': CERT, }
        mock_read_listings.return_value = {'/pulp/pulp/fedora-14/x86_64': 'repo-x'}
        mock_read_bundle.return_value = repo_x_bundle
        request_x = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')

        valid = oid_validation.authenticate(request_x, config=self.config)

        # Make sure we didn't call into the cert validation code
        self.assertEqual(validate_certificate_pem.call_count, 1)
        # It should be other because we mocked validate_certificate_pem to return False
        self.assertEqual(valid, False)
        # _check_extensions shouldn't have been called
        self.assertEqual(_check_extensions.call_count, 0)

    def test_basic_validate(self):
        repo_cert_utils = RepoCertUtils(config=self.config)

        cert_pem = E_FULL
        ca_pem = VALID_CA
        status = repo_cert_utils.validate_certificate_pem(cert_pem, ca_pem)
        self.assertTrue(status)
        status = self.simple_m2crypto_verify(cert_pem, ca_pem)
        self.assertTrue(status)

        cert_pem = E_FULL
        ca_pem = OTHER_CA
        status = repo_cert_utils.validate_certificate_pem(cert_pem, ca_pem)
        self.assertFalse(status)
        status = self.simple_m2crypto_verify(cert_pem, ca_pem)
        self.assertFalse(status)

        cert_pem = OTHER_CERT
        ca_pem = VALID_CA
        status = repo_cert_utils.validate_certificate_pem(cert_pem, ca_pem)
        self.assertFalse(status)
        status = self.simple_m2crypto_verify(cert_pem, ca_pem)
        self.assertFalse(status)

    def __test_scenario_1(self):
        """
        Setup
        - Global auth disabled
        - Individual repo auth enabled for repo X
        - Client cert signed by repo X CA
        - Client cert has entitlements

        Expected
        - Permitted for both repos
        """

        # Setup
        self.auth_api.disable_global_repo_auth()

        repo_x_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(E_FULL,
                                 'https://localhost//pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(E_FULL,
                                 'https://localhost//pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(response_y)

    @mock.patch(
        'pulp.repoauth.protected_repo_utils.ProtectedRepoUtils.read_protected_repo_listings')
    @mock.patch('pulp.repoauth.repo_cert_utils.RepoCertUtils.read_consumer_cert_bundle')
    @mock.patch('pulp.repoauth.repo_cert_utils.RepoCertUtils.read_global_cert_bundle')
    def test_scenario_2(self, mock_read_global_bundle, mock_read_bundle, mock_read_listings):
        """
        Setup
        - Global auth disabled
        - Individual repo auth enabled for repo X
        - Client cert signed by different CA than repo X
        - Client cert has entitlements

        Expected
        - Denied to repo X, permitted for repo Y
        """
        mock_read_global_bundle.return_value = None
        repo_x_bundle = {'ca': OTHER_CA, 'key': KEY, 'cert': CERT, }
        mock_read_listings.return_value = {'/pulp/pulp/fedora-14/x86_64': 'repo-x'}
        mock_read_bundle.return_value = repo_x_bundle

        # Test
        request_x = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(response_y)

    @mock.patch(
        'pulp.repoauth.protected_repo_utils.ProtectedRepoUtils.read_protected_repo_listings')
    @mock.patch('pulp.repoauth.repo_cert_utils.RepoCertUtils.read_consumer_cert_bundle')
    @mock.patch('pulp.repoauth.repo_cert_utils.RepoCertUtils.read_global_cert_bundle')
    def test_scenario_3(self, mock_read_global_bundle, mock_read_bundle, mock_read_listings):
        """
        Setup
        - Global auth disabled
        - Individual repo auth enabled for repo X
        - Client cert signed by repo Y CA
        - Client cert does not have entitlements for requested URL

        Expected
        - Permitted to repo X, denied from repo Y
        """
        mock_read_global_bundle.return_value = None

        repo_y_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        mock_read_listings.return_value = {'/pulp/pulp/fedora-13/x86_64': 'repo-x'}
        mock_read_bundle.return_value = repo_y_bundle

        # Test
        request_x = mock_environ(E_LIMITED,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(E_LIMITED,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(not response_y)

    def __test_scenario_4(self):
        """
        Setup
        - Global auth enabled
        - Individual auth disabled
        - Client cert signed by global CA
        - Client cert has entitlements to both repo X and Y

        Expected
        - Permitted to repo X and Y
        """

        # Setup
        global_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(response_y)

    def __test_scenario_5(self):
        """
        Setup
        - Global auth enabled
        - Individual auth disabled
        - Client cert signed by global CA
        - Client cert has entitlements to only repo X

        Expected
        - Permitted to repo X, denied to repo Y
        """

        # Setup
        global_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(E_LIMITED,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(E_LIMITED,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(not response_y)

    def __test_scenario_6(self):
        """
        Setup
        - Global auth enabled
        - Individual auth disabled
        - Client cert signed by non-global CA
        - Client cert has entitlements for both repos

        Expected
        - Denied to both repo X and Y
        """

        # Setup
        global_bundle = {'ca': OTHER_CA, 'key': KEY, 'cert': CERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(not response_y)

    def __test_scenario_7(self):
        """
        Setup
        - Global auth enabled
        - Individual auth enabled on repo X
        - Both global and individual auth use the same CA
        - Client cert signed by the specified CA
        - Client cert has entitlements for both repos

        Expected
        - Permitted for both repo X and Y
        """

        # Setup
        global_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(response_y)

    def __test_scenario_8(self):
        """
        Setup
        - Global auth enabled
        - Individual auth enabled on repo X
        - Different CA certificates for global and repo X configurations
        - Client cert signed by repo X's CA certificate
        - Client cert has entitlements for both repos

        Expected
        - Permitted for repo X, denied for repo Y
        """

        # Setup
        global_bundle = {'ca': OTHER_CA, 'key': KEY, 'cert': CERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(not response_y)

    def __test_scenario_9(self):
        """
        Setup
        - Global auth enabled
        - Individual auth enabled for repo X
        - Different CA certificates for global and repo X configurations
        - Client cert signed by global CA certificate
        - Client cert has entitlements for both repos

        Excepted
        - Denied for repo X, passes for repo Y
        """

        # Setup
        global_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca': OTHER_CA, 'key': KEY, 'cert': CERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ(E_FULL,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(response_y)

    def __test_scenario_10(self):
        """
        Setup
        - Global auth disabled
        - Individual repo auth enabled for repo X
        - No client cert in request

        Expected
        - Denied for repo X, permitted for repo Y
        - No exceptions thrown
        """

        # Setup
        self.auth_api.disable_global_repo_auth()

        repo_x_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ('',
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ('',
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(response_y)

    def __test_scenario_11(self):
        """
        Setup
        - Global auth enabled
        - Individual auth disabled
        - No client cert in request

        Expected
        - Denied to both repo X and Y
        - No exceptions thrown
        """

        # Setup
        global_bundle = {'ca': OTHER_CA, 'key': KEY, 'cert': CERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        self.repo_api.create('repo-x', 'Repo X', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ('',
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ('',
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(not response_y)

    def __test_scenario_12(self):
        """
        Setup
        - Global auth enabled
        - Individual auth enabled on repo X
        - Both global and individual auth use the same CA
        - No client cert in request

        Expected
        - Denied for both repo X and Y
        - No exceptions thrown
        """

        # Setup
        global_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        self.auth_api.enable_global_repo_auth(global_bundle)

        repo_x_bundle = {'ca': VALID_CA, 'key': KEY, 'cert': CERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ('',
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/')
        request_y = mock_environ('',
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(not response_x)
        self.assertTrue(not response_y)

    def __test_scenario_13(self):
        repo_x_bundle = {'ca': OTHER_CA, 'key': OTHER_CERT_KEY,
                         'cert': OTHER_CERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(E_WILDCARD,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-14/x86_64/os')
        request_y = mock_environ(E_WILDCARD,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64/os')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(response_y)

        # Try to hit something that should be denied
        request_z = mock_environ(E_WILDCARD,
                                 'https://localhost/pulp/repos/repos/pulp/pulp/fedora-13/x86_64'
                                 '/mrg-g/2.0/os')
        response_z = oid_validation.authenticate(request_z, config=self.config)
        self.assertTrue(not response_z)

    def __test_scenario_14(self):
        """
        Setup
        - Global auth disabled
        - Individual repo auth enabled for repo X
        - Client cert signed by repo X CA
        - Client cert has an OID entitlement that ends with a yum variable.
          e.g., repos/pulp/pulp/fedora-14/$basearch/

        Expected
        - Permitted for both repos
        """

        # Setup
        self.auth_api.disable_global_repo_auth()

        repo_x_bundle = {'ca': OTHER_CA, 'key': OTHER_CA_KEY, 'cert': CERT, }
        self.repo_api.create('repo-x', 'Repo X', 'noarch', consumer_cert_data=repo_x_bundle,
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64')
        self.repo_api.create('repo-y', 'Repo Y', 'noarch',
                             feed='http://repos.fedorapeople.org/repos/pulp/pulp/fedora-13/x86_64')

        # Test
        request_x = mock_environ(E_VARIABLE_CERT +
                                 E_VARIABLE_KEY,
                                 'https://localhost//pulp/repos/repos/pulp/pulp/fedora-14/x86_64'
                                 '/os/repodata/repomd.xml')
        request_xx = mock_environ(E_VARIABLE_CERT +
                                  E_VARIABLE_KEY,
                                  'https://localhost//pulp/repos/repos/pulp/pulp/fedora-14/i386'
                                  '/os/repodata/repomd.xml')
        request_y = mock_environ(E_VARIABLE_CERT +
                                 E_VARIABLE_KEY,
                                 'https://localhost//pulp/repos/repos/pulp/pulp/fedora-13/x86_64'
                                 '/os/repodata/repomd.xml')

        response_x = oid_validation.authenticate(request_x, config=self.config)
        response_xx = oid_validation.authenticate(request_xx, config=self.config)
        response_y = oid_validation.authenticate(request_y, config=self.config)

        # Verify
        self.assertTrue(response_x)
        self.assertTrue(response_y)
        self.assertTrue(response_xx)

    @mock.patch("pulp.oid_validation.oid_validation._config")
    @mock.patch("pulp.oid_validation.oid_validation.OidValidator")
    def test_authenticate_loads_config(self, mock_validator, mock_config):
        environ = mock_environ(E_FULL, 'https://nowhere/path/to')

        oid_validation.authenticate(environ)

        mock_config.assert_called_once_with()

    @mock.patch("pulp.oid_validation.oid_validation.SafeConfigParser")
    def test_config(self, mock_config_parser):
        mock_config_parser_instance = mock.Mock()
        mock_config_parser.return_value = mock_config_parser_instance

        oid_validation._config()

        mock_config_parser_instance.read.assert_called_once_with('/etc/pulp/repo_auth.conf')

    def test_get_repo_url_prefixes_from_config(self):
        mock_config = mock.Mock()
        mock_config.get.return_value = "a,b"

        validator = oid_validation.OidValidator(mock_config)
        result = validator._get_repo_url_prefixes_from_config(mock_config)

        self.assertEquals(result, ["a", "b"])

    def test_get_repo_url_prefixes_from_config_no_entry(self):
        """
        If we can't read the options, assert that we get a default
        """
        mock_config = mock.Mock()
        mock_config.get.side_effect = NoOptionError(None, None)

        validator = oid_validation.OidValidator(mock_config)
        result = validator._get_repo_url_prefixes_from_config(mock_config)

        self.assertEquals(result, ["/pulp/repos", "/pulp/ostree/web"])

    def test_no_mod_ssl_vars(self):
        """
        Test that if 'mod_ssl.var_lookup' is missing, it is handled gracefully.
        """
        environ = mock_environ(
            E_FULL,
            'https://localhost/some/repo/package.rpm'
        )
        environ.pop('mod_ssl.var_lookup')

        self.assertFalse(oid_validation.authenticate(environ))
        environ['wsgi.errors'].write.assert_called_once_with(
            'Authentication failed; no client certificate provided in request.\n'
        )

    @mock.patch('pulp.oid_validation.oid_validation.OidValidator')
    def test_ssl_client_cert_set(self, mock_oid_validation):
        """
        Test that if the client cert is in SSL_CLIENT_CERT, that certificate is used.

        It may be the case that 'SSL_CLIENT_CERT' is set in the 'environ' dictionary.
        It might also be the case that 'mod_ssl.var_lookup' is not set, and we should
        handle that case.
        """
        environ = mock_environ(
            E_FULL,
            'https://localhost/some/repo/package.rpm'
        )
        environ['SSL_CLIENT_CERT'] = E_FULL
        environ.pop('mod_ssl.var_lookup')
        mock_oid_validation.return_value.is_valid.return_value = True

        self.assertTrue(oid_validation.authenticate(environ))
        mock_oid_validation.return_value.is_valid.assert_called_once_with(
            '/some/repo/package.rpm', E_FULL, environ['wsgi.errors'].write)

    @mock.patch('pulp.oid_validation.oid_validation.certificate')
    def test_check_extensions(self, mock_certificate_module):
        """Assert path prefixes are stripped correctly before handing the path to RHSM"""
        path_prefixes = ['/pulp/repos', '/pulp/ostree/', '/some/prefix']
        unprefixed_path = '/content/i/want'
        prefixed_paths = [
            '/pulp/repos/content/i/want',
            '/pulp/ostree/content/i/want',
            '/some/prefix/content/i/want',
        ]
        mock_cert = mock.Mock()
        mock_certificate_module.create_from_pem.return_value = mock_cert
        validator = oid_validation.OidValidator(self.config)

        for path in prefixed_paths:
            validator._check_extensions(mock.Mock(), path, mock.Mock(), path_prefixes)

        for call in mock_cert.check_path.call_args_list:
            self.assertEqual(unprefixed_path, call[0][0])
