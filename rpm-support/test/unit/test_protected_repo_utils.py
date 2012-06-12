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

from ConfigParser import SafeConfigParser
import os
import unittest

from pulp_rpm.repo_auth.protected_repo_utils import ProtectedRepoListingFile, ProtectedRepoUtils

# -- constants -----------------------------------------------------------------------

TEST_FILE = '/tmp/test-protected-repo-listing'

CONFIG = SafeConfigParser()
CONFIG.read([os.path.abspath(os.path.dirname(__file__)) + '/data/test-override-pulp.conf',
             os.path.abspath(os.path.dirname(__file__)) + '/data/test-override-repoauth.conf'])

# -- test cases ----------------------------------------------------------------------

class TestProtectedRepoUtils(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)
        self.utils = ProtectedRepoUtils(CONFIG)

    def tearDown(self):
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)

    def test_add_protected_repo(self):
        """
        Tests adding a protected repo.
        """

        # Setup
        repo_id = 'prot-repo-1'
        relative_path = 'path-1'

        # Test
        self.utils.add_protected_repo(relative_path, repo_id)

        # Verify
        listings = self.utils.read_protected_repo_listings()

        self.assertEqual(1, len(listings))
        self.assertTrue(relative_path in listings)
        self.assertEqual(listings[relative_path], repo_id)

    def test_delete_protected_repo(self):
        """
        Tests deleting an existing protected repo.
        """

        # Setup
        repo_id = 'prot-repo-1'
        relative_path = 'path-1'
        self.utils.add_protected_repo(relative_path, repo_id)

        # Test
        self.utils.delete_protected_repo(relative_path)

        # Verify
        listings = self.utils.read_protected_repo_listings()

        self.assertEqual(0, len(listings))
        
class TestProtectedRepoListingFile(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)

    def tearDown(self):
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)

    def test_save_load_delete_with_repos(self):
        """
        Tests saving, reloading, and then deleting the listing file.
        """

        # Test Save
        f = ProtectedRepoListingFile(TEST_FILE)
        f.add_protected_repo_path('foo', 'repo1')
        f.save()

        # Verify Save
        self.assertTrue(os.path.exists(TEST_FILE))

        # Test Load
        f = ProtectedRepoListingFile(TEST_FILE)
        f.load()

        # Verify Load
        self.assertEqual(1, len(f.listings))
        self.assertTrue('foo' in f.listings)
        self.assertEqual('repo1', f.listings['foo'])

        # Test Delete
        f.delete()

        # Verify Delete
        self.assertTrue(not os.path.exists(TEST_FILE))

    def test_create_no_filename(self):
        """
        Tests that creating the protected repo file without specifying a name
        throws the proper exception.
        """
        self.assertRaises(ValueError, ProtectedRepoListingFile, None)

    def test_remove_repo_path(self):
        """
        Tests removing a repo path successfully removes it from the listings.
        """

        # Setup
        f = ProtectedRepoListingFile(TEST_FILE)
        f.add_protected_repo_path('foo', 'repo1')

        self.assertEqual(1, len(f.listings))

        # Test
        f.remove_protected_repo_path('foo')

        # Verify
        self.assertEqual(0, len(f.listings))

    def test_remove_non_existent(self):
        """
        Tests removing a path that isn't in the file does not throw an error.
        """

        # Setup
        f = ProtectedRepoListingFile(TEST_FILE)
        f.add_protected_repo_path('foo', 'repo1')

        self.assertEqual(1, len(f.listings))

        # Test
        f.remove_protected_repo_path('bar') # should not error

        # Verify
        self.assertEqual(1, len(f.listings))
