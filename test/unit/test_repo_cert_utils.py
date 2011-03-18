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

import pulp.server.repo_cert_utils as utils
import testutil


CERT_DIR = '/tmp/test_repo_cert_utils/repos'


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

    def setUp(self):
        self.config = testutil.load_test_config()
        self.config.set('repos', 'cert_location', CERT_DIR)

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
        utils.write_feed_cert_bundle(repo_id, bundle)

        # Verify
        repo_cert_dir = utils._cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        self._verify_file_contents(repo_id, 'feed-%s.ca' % repo_id, bundle['ca'])
        self._verify_file_contents(repo_id, 'feed-%s.cert' % repo_id, bundle['cert'])
        self._verify_file_contents(repo_id, 'feed-%s.key' % repo_id, bundle['key'])

    def test_write_consumer_certs(self):
        '''
        Tests writing repo consumer certificates to disk.        
        '''

        # Setup
        repo_id = 'test-repo-1'
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        # Test
        utils.write_consumer_cert_bundle(repo_id, bundle)

        # Verify
        repo_cert_dir = utils._cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        self._verify_file_contents(repo_id, 'consumer-%s.ca' % repo_id, bundle['ca'])
        self._verify_file_contents(repo_id, 'consumer-%s.cert' % repo_id, bundle['cert'])
        self._verify_file_contents(repo_id, 'consumer-%s.key' % repo_id, bundle['key'])

    def test_delete_bundles(self):
        '''
        Tests deleting bundles for a repo.
        '''

        # Setup
        repo_id = 'test-repo-2'
        bundle = {'ca' : 'FOO', 'cert' : 'BAR', 'key' : 'BAZ'}

        utils.write_feed_cert_bundle(repo_id, bundle)
        utils.write_consumer_cert_bundle(repo_id, bundle)

        repo_cert_dir = utils._cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        cert_files = os.listdir(repo_cert_dir)
        self.assertEqual(6, len(cert_files)) # 2 bundles, 3 files each

        # Test
        utils.delete_for_repo(repo_id)

        # Verify
        self.assertTrue(not os.path.exists(repo_cert_dir))
        
    def _verify_file_contents(self, repo_id, filename, contents):
        full_filename = os.path.join(utils._cert_directory(repo_id), filename)
        f = open(full_filename, 'r')
        read_contents = f.read()
        f.close()

        self.assertEqual(read_contents, contents)
