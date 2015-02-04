from ConfigParser import SafeConfigParser

import mock
import os
import shutil
import unittest

from pulp.repoauth.protected_repo_utils import ProtectedRepoListingFile, ProtectedRepoUtils


# -- constants -----------------------------------------------------------------------

TEST_FILE = '/tmp/test-protected-repo-listing'
DATA_DIR = os.path.abspath(os.path.dirname(__file__)) + '/data'

CONFIG = SafeConfigParser()
CONFIG.read([os.path.join(DATA_DIR, 'test-override-pulp.conf'),
             os.path.join(DATA_DIR, 'test-override-repoauth.conf')])


class TestProtectedRepoUtils(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)
        self.utils = ProtectedRepoUtils(CONFIG)

    def tearDown(self):
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)
        global_cert_location = CONFIG.get('repos', 'global_cert_location')
        if os.path.exists(global_cert_location):
            shutil.rmtree(global_cert_location)

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
        global_cert_location = CONFIG.get('repos', 'global_cert_location')
        if os.path.exists(global_cert_location):
            shutil.rmtree(global_cert_location)

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

    def test_load_allow_missing(self):
        f = ProtectedRepoListingFile("/a/nonexistant/path")
        result = f.load()
        self.assertEquals(result, None)

    @mock.patch("os.makedirs")
    @mock.patch("os.path.exists")
    @mock.patch("os.path.split")
    @mock.patch("__builtin__.open")
    def test_save_creates_new_dir(self, mock_open, mock_split, mock_exists, mock_makedirs):
        mock_exists.return_value = False

        f = ProtectedRepoListingFile("/a/nonexistant/path")
        f.save()

        mock_makedirs.assert_called_once()

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
        f.remove_protected_repo_path('bar')  # should not error

        # Verify
        self.assertEqual(1, len(f.listings))
