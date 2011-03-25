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
import shutil
import sys
import os
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import pulp.repo_auth.repo_cert_utils as utils
from pulp.repo_auth.repo_cert_utils import ProtectedRepoListingFile
import testutil

# -- constants -----------------------------------------------------------------------

CERT_DIR = '/tmp/test_repo_cert_utils/repos'
GLOBAL_CERT_DIR = '/tmp/test_repo_cert_utils/global'

# Used to sign the test certificate
VALID_CA = os.path.abspath(os.path.dirname(__file__)) + '/data/test_repo_cert_utils/valid_ca.crt'

# Not used to sign the test certificate  :)
INVALID_CA = os.path.abspath(os.path.dirname(__file__)) + '/data/test_repo_cert_utils/invalid_ca.crt'

# Test certificate
CERT = os.path.abspath(os.path.dirname(__file__)) + '/data/test_repo_cert_utils/cert.crt'

# -- test cases ----------------------------------------------------------------------

class TestValidateCertBundle(unittest.TestCase):

    def test_validate_cert_bundle_valid(self):
        '''
        Tests that validating a valid cert bundle does not indicate an error.
        '''

        # Setup
        bundle = {'ca' : 'PEM', 'cert' : 'PEM', 'key' : 'PEM'}

        # Test
        utils.validate_cert_bundle(bundle) # should not throw an error

    def test_validate_cert_bundle_missing_keys(self):
        '''
        Tests that a cert bundle missing any of the required keys indicates
        an error.
        '''

        # Test missing CA
        self.assertRaises(ValueError, utils.validate_cert_bundle, {'cert' : 'PEM', 'key' : 'PEM'})
        self.assertRaises(ValueError, utils.validate_cert_bundle, {'ca' : 'PEM', 'key' : 'PEM'})
        self.assertRaises(ValueError, utils.validate_cert_bundle, {'ca' : 'PEM', 'cert' : 'PEM'})

    def test_validate_cert_bundle_non_dict(self):
        '''
        Tests that calling validate without passing a dict correctly indicates
        an error.
        '''

        # Test bad parameter
        self.assertRaises(ValueError, utils.validate_cert_bundle, 'foo')

    def test_validate_cert_bundle_none(self):
        '''
        Tests that calling validate with None throws the correct error.
        '''

        # Test missing parameter
        self.assertRaises(ValueError, utils.validate_cert_bundle, None)

    def test_validate_cert_bundle_extra_keys(self):
        '''
        Tests that calling validate with non-cert bundle keys raises an error.
        '''

        # Setup
        bundle = {'ca' : 'PEM', 'cert' : 'PEM', 'key' : 'PEM', 'foo' : 'bar'}

        # Test
        self.assertRaises(ValueError, utils.validate_cert_bundle, bundle)


class TestCertStorage(unittest.TestCase):

    def clean(self):
        if os.path.exists(CERT_DIR):
            shutil.rmtree(CERT_DIR)

        if os.path.exists(GLOBAL_CERT_DIR):
            shutil.rmtree(GLOBAL_CERT_DIR)

    def setUp(self):
        self.config = testutil.load_test_config()
        self.config.set('repos', 'cert_location', CERT_DIR)
        self.config.set('repos', 'global_cert_location', GLOBAL_CERT_DIR)

        self.clean()

    def tearDown(self):
        self.clean()

    def test_write_feed_certs(self):
        '''
        Tests writing repo feed certificates to disk.
        '''

        # Setup
        repo_id = 'test-repo-1'
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        # Test
        files = utils.write_feed_cert_bundle(repo_id, bundle)

        # Verify
        self.assertTrue(files is not None)
        self.assertEqual(3, len(files))

        repo_cert_dir = utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        self._verify_repo_file_contents(repo_id, 'feed-%s.ca' % repo_id, bundle['ca'])
        self._verify_repo_file_contents(repo_id, 'feed-%s.cert' % repo_id, bundle['cert'])
        self._verify_repo_file_contents(repo_id, 'feed-%s.key' % repo_id, bundle['key'])

    def test_write_consumer_certs(self):
        '''
        Tests writing repo consumer certificates to disk.        
        '''

        # Setup
        repo_id = 'test-repo-1'
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        # Test
        files = utils.write_consumer_cert_bundle(repo_id, bundle)

        # Verify
        self.assertTrue(files is not None)
        self.assertEqual(3, len(files))

        repo_cert_dir = utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        self._verify_repo_file_contents(repo_id, 'consumer-%s.ca' % repo_id, bundle['ca'])
        self._verify_repo_file_contents(repo_id, 'consumer-%s.cert' % repo_id, bundle['cert'])
        self._verify_repo_file_contents(repo_id, 'consumer-%s.key' % repo_id, bundle['key'])

    def test_write_read_global_certs(self):
        '''
        Tests writing out the global repo cert bundle.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        # Test Write
        files = utils.write_global_repo_cert_bundle(bundle)

        # Verify Write
        self.assertTrue(files is not None)
        self.assertEqual(3, len(files))

        global_cert_dir = utils._global_cert_directory()
        self.assertTrue(os.path.exists(global_cert_dir))

        # -----

        # Test Read All
        read_bundle = utils.read_global_cert_bundle()

        # Verify Read All
        self.assertTrue(read_bundle is not None)
        self.assertEqual(read_bundle, bundle)

        # -----

        # Test Read Subset
        read_bundle  = utils.read_global_cert_bundle(['key'])

        # Verify Read Subset
        self.assertTrue(read_bundle is not None)
        self.assertEqual(1, len(read_bundle))
        self.assertTrue('key' in read_bundle)
        self.assertEqual(read_bundle['key'], bundle['key'])
        
    def test_write_read_partial_bundle(self):
        '''
        Tests that only a subset of the bundle components can be specified and still
        correctly written out.
        '''

        # Setup
        bundle = {'ca' : 'FOO'}

        # Test
        files = utils.write_global_repo_cert_bundle(bundle)

        # Verify
        self.assertTrue(files is not None)
        self.assertEqual(1, len(files))

        global_cert_dir = utils._global_cert_directory()
        self.assertTrue(os.path.exists(global_cert_dir))

        read_bundle = utils.read_global_cert_bundle(['ca'])

        self.assertEqual(read_bundle['ca'], bundle['ca'])

        self.assertTrue(not os.path.exists(os.path.join(utils._global_cert_directory(), 'pulp-global-repo.cert')))
        self.assertTrue(not os.path.exists(os.path.join(utils._global_cert_directory(), 'pulp-global-repo.key')))

    def test_read_global_no_bundle(self):
        '''
        Tests that attempting to read the global repo bundle when it doesn't exist
        returns None.
        '''

        # Test
        bundle = utils.read_global_cert_bundle()

        # Verify
        self.assertTrue(bundle is None)

    def test_delete_bundles(self):
        '''
        Tests deleting bundles for a repo.
        '''

        # Setup
        repo_id = 'test-repo-2'
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        utils.write_feed_cert_bundle(repo_id, bundle)
        utils.write_consumer_cert_bundle(repo_id, bundle)

        repo_cert_dir = utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        cert_files = os.listdir(repo_cert_dir)
        self.assertEqual(6, len(cert_files)) # 2 bundles, 3 files each

        # Test
        utils.delete_for_repo(repo_id)

        # Verify
        self.assertTrue(not os.path.exists(repo_cert_dir))

    def test_delete_global_bundle(self):
        '''
        Tests deleting the global repo auth bundle.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        utils.write_global_repo_cert_bundle(bundle)

        # Test
        utils.delete_global_cert_bundle()

        # Verify
        read_bundle = utils.read_global_cert_bundle()
        self.assertTrue(read_bundle is None)

    def _verify_repo_file_contents(self, repo_id, filename, contents):
        full_filename = os.path.join(utils._repo_cert_directory(repo_id), filename)
        f = open(full_filename, 'r')
        read_contents = f.read()
        f.close()

        self.assertEqual(read_contents, contents)

class TestCertVerify(unittest.TestCase):

    def test_valid(self):
        '''
        Tests that verifying a cert with its signing CA returns true.
        '''
        self.assertTrue(utils.validate_certificate(CERT, VALID_CA))

    def test_invalid(self):
        '''
        Tests that verifying a cert with an incorrect CA returns false.
        '''
        self.assertTrue(not utils.validate_certificate(CERT, INVALID_CA))

    def test_valid_pem(self):
        '''
        Tests that verifying a PEM encoded cert string with its signing CA returns true.
        '''

        # Setup
        f = open(VALID_CA)
        ca = f.read()
        f.close()

        f = open(CERT)
        cert = f.read()
        f.close()

        # Test
        self.assertTrue(utils.validate_certificate_pem(cert, ca))

    def test_invalid_pem(self):
        '''
        Tests that verifying a PEM encoded cert string with an incorrect CA returns false.
        '''

        # Setup
        f = open(INVALID_CA)
        ca = f.read()
        f.close()

        f = open(CERT)
        cert = f.read()
        f.close()

        # Test
        self.assertTrue(not utils.validate_certificate_pem(cert, ca))

class TestProtectedRepoListingFile(unittest.TestCase):

    TEST_FILE = '/tmp/test-protected-repo-listing'

    def setUp(self):
        if os.path.exists(TestProtectedRepoListingFile.TEST_FILE):
            os.remove(TestProtectedRepoListingFile.TEST_FILE)

    def tearDown(self):
        if os.path.exists(TestProtectedRepoListingFile.TEST_FILE):
            os.remove(TestProtectedRepoListingFile.TEST_FILE)

    def test_save_load_delete_with_repos(self):
        '''
        Tests saving, reloading, and then deleting the listing file.
        '''

        # Test Save
        f = ProtectedRepoListingFile(TestProtectedRepoListingFile.TEST_FILE)
        f.add_protected_repo_path('foo', 'repo1')
        f.save()

        # Verify Save
        self.assertTrue(os.path.exists(TestProtectedRepoListingFile.TEST_FILE))

        # Test Load
        f = ProtectedRepoListingFile(TestProtectedRepoListingFile.TEST_FILE)
        f.load()

        # Verify Load
        self.assertEqual(1, len(f.listings))
        self.assertTrue('foo' in f.listings)
        self.assertEqual('repo1', f.listings['foo'])

        # Test Delete
        f.delete()

        # Verify Delete
        self.assertTrue(not os.path.exists(TestProtectedRepoListingFile.TEST_FILE))

    def test_create_no_filename(self):
        '''
        Tests that creating the protected repo file without specifying a name
        throws the proper exception.
        '''
        self.assertRaises(ValueError, ProtectedRepoListingFile, None)

    def test_remove_repo_path(self):
        '''
        Tests removing a repo path successfully removes it from the listings.
        '''

        # Setup
        f = ProtectedRepoListingFile(TestProtectedRepoListingFile.TEST_FILE)
        f.add_protected_repo_path('foo', 'repo1')

        self.assertEqual(1, len(f.listings))

        # Test
        f.remove_protected_repo_path('foo')

        # Verify
        self.assertEqual(0, len(f.listings))

    def test_remove_non_existent(self):
        '''
        Tests removing a path that isn't in the file does not throw an error.
        '''

        # Setup
        f = ProtectedRepoListingFile(TestProtectedRepoListingFile.TEST_FILE)
        f.add_protected_repo_path('foo', 'repo1')

        self.assertEqual(1, len(f.listings))

        # Test
        f.remove_protected_repo_path('bar') # should not error

        # Verify
        self.assertEqual(1, len(f.listings))
        