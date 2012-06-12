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
from ConfigParser import DuplicateSectionError
import os
import shutil
import unittest

from pulp_rpm.common.repo_file import Repo, RepoFile, MirrorListFile, RepoKeyFiles, CertFiles

TEST_REPO_FILENAME = '/tmp/TestRepoFile.repo'
TEST_MIRROR_LIST_FILENAME = '/tmp/TestRepoFile.mirrorlist'
TEST_KEYS_ROOT_DIR = '/tmp/TestRepoFile-keys'
TEST_CERT_ROOT_DIR = '/tmp/TestRepoFile-Certificates'

# -- repo file tests ------------------------------------------------------------------

class TestRepoFile(unittest.TestCase):

    def setUp(self):
        # Clean up from any previous runs that may have exited abnormally
        if os.path.exists(TEST_REPO_FILENAME):
            os.remove(TEST_REPO_FILENAME)

    def tearDown(self):
        # Clean up in case the test file was saved in a test
        if os.path.exists(TEST_REPO_FILENAME):
            os.remove(TEST_REPO_FILENAME)

    def test_one_repo_save_and_load(self):
        """
        Tests the normal flow of saving and loading, using only one repo to
        minimize complications.
        """

        # Setup
        add_me = Repo('test-repo-1')
        add_me['baseurl'] = 'http://localhost/repo'
        add_me['enabled'] = 1
        add_me['gpgkey'] = '/tmp/key'
        add_me['sslverify'] = 0
        add_me['gpgcheck'] = 0
        add_me['sslcacert'] = '/tmp/sslcacert'
        add_me['sslclientcert'] = '/tmp/clientcert'

        repo_file = RepoFile(TEST_REPO_FILENAME)

        # Test Save
        repo_file.add_repo(add_me)
        repo_file.save()

        # Verify Save
        self.assertTrue(os.path.exists(TEST_REPO_FILENAME))

        # Test Load
        loaded = RepoFile(TEST_REPO_FILENAME)
        loaded.load()

        # Verify Load
        self.assertEqual(1, len(loaded.all_repos()))

        found_repo = loaded.get_repo('test-repo-1')
        self.assertTrue(found_repo is not None)
        self.assertTrue(_repo_eq(add_me, found_repo))

    def test_multiple_repos(self):
        """
        Tests saving and loading multiple repos.
        """

        # Setup
        repo1 = Repo('test-repo-1')
        repo1['baseurl'] = 'http://localhost/repo1'

        repo2 = Repo('test-repo-2')
        repo2['baseurl'] = 'http://localhost/repo2'

        repo_file = RepoFile(TEST_REPO_FILENAME)

        # Test
        repo_file.add_repo(repo1)
        repo_file.add_repo(repo2)
        repo_file.save()

        # Verify
        loaded = RepoFile(TEST_REPO_FILENAME)
        loaded.load()

        self.assertEqual(2, len(loaded.all_repos()))

        found_repo1 = loaded.get_repo('test-repo-1')
        self.assertTrue(found_repo1 is not None)
        self.assertTrue(_repo_eq(repo1, found_repo1))

        found_repo2 = loaded.get_repo('test-repo-2')
        self.assertTrue(found_repo2 is not None)
        self.assertTrue(_repo_eq(repo2, found_repo2))

    def test_add_duplicate(self):
        """
        Tests that adding a repo that already exists throws a duplication error.
        """

        # Setup
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.add_repo(Repo('foo'))

        # Test
        self.assertRaises(DuplicateSectionError, repo_file.add_repo, Repo('foo'))


    def test_delete_repo(self):
        """
        Tests removing an existing repo is correctly saved and loaded
        """

        # Setup
        repo1 = Repo('test-repo-1')
        repo2 = Repo('test-repo-2')

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.add_repo(repo1)
        repo_file.add_repo(repo2)
        repo_file.save()
        
        # Test
        repo_file.remove_repo_by_name('test-repo-1')
        repo_file.save()

        # Verify
        loaded = RepoFile(TEST_REPO_FILENAME)
        loaded.load()
        
        self.assertEqual(1, len(loaded.all_repos()))

        self.assertTrue(loaded.get_repo('test-repo-1') is None)
        self.assertTrue(loaded.get_repo('test-repo-2') is not None)

    def test_delete_repo_no_repo(self):
        """
        Ensures that an error is not thrown when a repo that does not exist is
        deleted from the repo file.
        """

        # Setup
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.add_repo(Repo('test-repo-1'))

        # Test
        repo_file.remove_repo_by_name('foo')

        # Verify
        self.assertTrue(repo_file.get_repo('test-repo-1') is not None)

    def test_update_repo(self):
        """
        Tests that updating an existing repo is correctly saved.
        """

        # Setup
        repo1 = Repo('test-repo-1')
        repo1['baseurl'] = 'http://localhost/repo1'

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.add_repo(repo1)
        repo_file.save()

        # Test
        repo1['baseurl'] = 'http://localhost/repo-updated'
        repo_file.update_repo(repo1)
        repo_file.save()

        # Verify
        loaded = RepoFile(TEST_REPO_FILENAME)
        loaded.load()

        found_repo = loaded.get_repo('test-repo-1')
        self.assertEqual(found_repo['baseurl'], 'http://localhost/repo-updated')

    def test_no_repos_save_load(self):
        """
        Tests that saving and loading a file with no repos is successful.
        """

        # Test
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.save()

        # Verify
        loaded = RepoFile(TEST_REPO_FILENAME)
        loaded.load()

        # Verify
        self.assertEqual(0, len(loaded.all_repos()))

    def test_delete_repofile(self):
        """
        Tests that deleting a RepoFile correctly deletes the file on disk.
        """

        # Setup
        self.assertTrue(not os.path.exists(TEST_REPO_FILENAME))

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.save()

        self.assertTrue(os.path.exists(TEST_REPO_FILENAME))

        # Test
        repo_file.delete()

        # Verify
        self.assertTrue(not os.path.exists(TEST_REPO_FILENAME))

    def test_broken_save(self):
        """
        Tests that an exception is raised when the file cannot be saved.
        """

        # Test

        # RepoFile will not create these directories so it should fail if this structure
        # does not exist.
        repo_file = RepoFile('/a/b/c/d')
        
        self.assertRaises(IOError, repo_file.save)

    def test_broken_load(self):
        """
        Tests that an exception is raised when the file cannot be loaded because it is not
        found.
        """

        # Test
        repo_file = RepoFile('/a/b/c/d')

        self.assertRaises(IOError, repo_file.load, allow_missing=False)

    def test_broken_load_allow_missing(self):
        """
        Tests that an exception is raised when the file cannot be loaded because it is not
        found.
        """

        # Test
        repo_file = RepoFile('/a/b/c/d')
        repo_file.load(allow_missing=True)

        # Verify
        # The above should not throw an error even though the file doesn't exist

    def test_broken_load_invalid_data(self):
        """
        Tests that an exception is raised when the file contains non-parsable data.
        """

        # Setup
        f = open(TEST_REPO_FILENAME, 'w')
        f.write('This is not parsable.')
        f.close()

        # Test
        repo_file = RepoFile(TEST_REPO_FILENAME)

        self.assertRaises(Exception, repo_file.load)

    def test_delete_file_doesnt_exist(self):
        """
        Tests that deleting when the file doesn't exist does *not* throw an error.
        """

        # Setup
        self.assertTrue(not os.path.exists(TEST_REPO_FILENAME))

        # Test
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.delete()

        # Verify
        # Nothing to verify, this shouldn't have thrown an error

    def test_header(self):
        """
        Tests that the pulp header is properly written in the generated file.
        """

        # Setup
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.save()

        # Test
        f = open(TEST_REPO_FILENAME, 'r')
        contents = f.read()
        f.close()

        # Verify
        self.assertTrue(contents.startswith(RepoFile.FILE_HEADER))

    def test_get_invalid_repo(self):
        """
        Makes sure None is returned when requesting a repo that doesn't exist
        instead of throwing an error.
        """

        # Setup
        repo_file = RepoFile(TEST_REPO_FILENAME)

        # Test
        found = repo_file.get_repo('foo')

        # Verify
        self.assertTrue(found is None)

    def test_missing_filename(self):
        """
        Tests that the proper error is thrown when creating a RepoFile without
        a filename.
        """

        # Test
        self.assertRaises(ValueError, RepoFile, None)

    def test_baseurl_not_mirrorlist(self):
        """
        Tests that if a baseurl is specified, a mirrorlist entry isn't written to the
        saved repo file.
        """

        # Setup
        repo = Repo('test-repo-1')
        repo['baseurl'] = 'http://localhost'

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.add_repo(repo)
        repo_file.save()

        # Test
        loaded = RepoFile(TEST_REPO_FILENAME)
        loaded.load()

        loaded_repo = loaded.get_repo('test-repo-1')
        self.assertEqual(loaded_repo['baseurl'], 'http://localhost')
        self.assertTrue('mirrorlist' not in loaded_repo)

    def test_mirrorlist_not_baseurl(self):
        """
        Tests that if a mirrorlist is specified, a baseurl entry isn't written to the
        saved repo file.
        """

        # Setup
        repo = Repo('test-repo-1')
        repo['mirrorlist'] = 'file://etc/pulp/mirrorlist'

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.add_repo(repo)
        repo_file.save()

        # Test
        loaded = RepoFile(TEST_REPO_FILENAME)
        loaded.load()

        loaded_repo = loaded.get_repo('test-repo-1')
        self.assertEqual(loaded_repo['mirrorlist'], 'file://etc/pulp/mirrorlist')
        self.assertTrue('baseurl' not in loaded_repo)

# -- mirror list tests ----------------------------------------------------------------

class TestMirrorListFile(unittest.TestCase):

    def setUp(self):
        # Clean up from any previous runs that may have exited abnormally
        if os.path.exists(TEST_MIRROR_LIST_FILENAME):
            os.remove(TEST_MIRROR_LIST_FILENAME)

    def tearDown(self):
        # Clean up in case the test file was saved in a test
        if os.path.exists(TEST_MIRROR_LIST_FILENAME):
            os.remove(TEST_MIRROR_LIST_FILENAME)

    def test_missing_filename(self):
        """
        Tests that a MirrorListFile cannot be created without specifying a filename.
        """

        # Test
        self.assertRaises(ValueError, MirrorListFile, None)

    def test_multiple_entries_save_load(self):
        """
        Tests creating a new mirror list file with multiple entries, saving it, and then
        loading it back from disk.
        """

        # Test Save
        mirror_list = MirrorListFile(TEST_MIRROR_LIST_FILENAME)
        mirror_list.add_entry('http://cds-01')
        mirror_list.add_entry('http://cds-02')

        mirror_list.save()

        # Verify Save
        self.assertTrue(os.path.exists(TEST_MIRROR_LIST_FILENAME))

        # Test Load
        loaded = MirrorListFile(TEST_MIRROR_LIST_FILENAME)
        loaded.load()

        # Verify Load
        self.assertEqual(2, len(loaded.entries))

        #   Make sure the entries are returned in the correct order
        self.assertEqual('http://cds-01', loaded.entries[0])
        self.assertEqual('http://cds-02', loaded.entries[1])

    def test_add_entries(self):
        """
        Tests the ability to add a list of entries in a single operation.
        """

        # Setup
        mirror_list = MirrorListFile(TEST_MIRROR_LIST_FILENAME)
        mirror_list.add_entry('http://cds-01')

        add_us = ['http://cds-02', 'http://cds-03']

        # Test
        mirror_list.add_entries(add_us)

        # Verify
        self.assertEqual(3, len(mirror_list.entries))

    def test_broken_save(self):
        """
        Tests that an exception is raised when the file cannot be saved.
        """

        # Test

        # MirrorListFile will not create these directories so it should fail if this structure
        # does not exist.
        mirror_list = MirrorListFile('/a/b/c/d')

        self.assertRaises(IOError, mirror_list.save)

    def test_broken_load(self):
        """
        Tests that an exception is raised when the file cannot be loaded because it is not
        found.
        """

        # Test
        mirror_list = MirrorListFile('/a/b/c/d')

        self.assertRaises(IOError, mirror_list.load)

    def test_delete_file_doesnt_exist(self):
        """
        Tests that deleting when the file doesn't exist does *not* throw an error.
        """

        # Setup
        self.assertTrue(not os.path.exists(TEST_MIRROR_LIST_FILENAME))

        # Test
        mirror_list = MirrorListFile(TEST_MIRROR_LIST_FILENAME)
        mirror_list.delete()

        # Verify
        # Nothing to verify, this shouldn't have thrown an error

# -- repo key files tests ----------------------------------------------------------------

class TestRepoKeyFiles(unittest.TestCase):

    def setUp(self):
        # Clean up from any previous runs that may have exited abnormally
        if os.path.exists(TEST_KEYS_ROOT_DIR):
            shutil.rmtree(TEST_KEYS_ROOT_DIR)

    def tearDown(self):
        # Clean up in case the test file was saved in a test
        if os.path.exists(TEST_KEYS_ROOT_DIR):
            shutil.rmtree(TEST_KEYS_ROOT_DIR)

    def test_repo_first_time(self):
        """
        Tests adding keys to a repo that has never had keys before (i.e. the
        repo keys dir doesn't exist).
        """

        # Test
        repo_keys = RepoKeyFiles(TEST_KEYS_ROOT_DIR, 'repo1')
        repo_keys.add_key('key1', 'KEY1')
        repo_keys.add_key('key2', 'KEY2')
        repo_keys.update_filesystem()

        # Verify
        self.assertTrue(os.path.exists(os.path.join(TEST_KEYS_ROOT_DIR, 'repo1')))

        key_files = repo_keys.key_filenames()
        self.assertEqual(2, len(key_files))

        for f in key_files:
            self.assertTrue(os.path.exists(f))

        f = open(key_files[0], 'r')
        contents = f.read()
        f.close()
        self.assertEqual(contents, 'KEY1')

        f = open(key_files[1], 'r')
        contents = f.read()
        f.close()
        self.assertEqual(contents, 'KEY2')

    def test_repo_existing_keys(self):
        """
        Tests adding a new key when keys have already been written. The new key should be
        present but the old should be deleted.
        """

        # Setup
        repo_keys = RepoKeyFiles(TEST_KEYS_ROOT_DIR, 'repo2')
        repo_keys.add_key('key1', 'KEY1')
        repo_keys.update_filesystem()

        # Test
        repo_keys = RepoKeyFiles(TEST_KEYS_ROOT_DIR, 'repo2')
        repo_keys.add_key('keyX', 'KEYX')
        repo_keys.update_filesystem()

        # Verify
        self.assertTrue(os.path.exists(os.path.join(TEST_KEYS_ROOT_DIR, 'repo2')))

        key_files = repo_keys.key_filenames()
        self.assertEqual(1, len(key_files))

        self.assertTrue(os.path.exists(os.path.join(TEST_KEYS_ROOT_DIR, 'repo2', 'keyX')))
        self.assertTrue(not os.path.exists(os.path.join(TEST_KEYS_ROOT_DIR, 'repo2', 'key1')))

        f = open(key_files[0], 'r')
        contents = f.read()
        f.close()
        self.assertEqual(contents, 'KEYX')

    def test_repo_update_key(self):
        """
        Tests adding new contents for a key that already exists.
        """

        # Setup
        repo_keys = RepoKeyFiles(TEST_KEYS_ROOT_DIR, 'repo3')
        repo_keys.add_key('key', 'KEY1')
        repo_keys.update_filesystem()

        # Test
        repo_keys = RepoKeyFiles(TEST_KEYS_ROOT_DIR, 'repo3')
        repo_keys.add_key('key', 'KEYX')
        repo_keys.update_filesystem()

        # Verify
        self.assertTrue(os.path.exists(os.path.join(TEST_KEYS_ROOT_DIR, 'repo3')))

        key_files = repo_keys.key_filenames()
        self.assertEqual(1, len(key_files))

        self.assertTrue(os.path.exists(os.path.join(TEST_KEYS_ROOT_DIR, 'repo3', 'key')))

        f = open(key_files[0], 'r')
        contents = f.read()
        f.close()
        self.assertEqual(contents, 'KEYX')

    def test_repo_remove_keys(self):
        """
        Tests calling update_filesystem for a repo that previously had keys but no longer
        does.
        """

        # Setup
        repo_keys = RepoKeyFiles(TEST_KEYS_ROOT_DIR, 'repo4')
        repo_keys.add_key('key', 'KEY1')
        repo_keys.update_filesystem()

        self.assertTrue(os.path.exists(repo_keys.key_filenames()[0]))

        # Test
        repo_keys = RepoKeyFiles(TEST_KEYS_ROOT_DIR, 'repo4')
        repo_keys.update_filesystem()

        # Verify
        self.assertTrue(not os.path.exists(os.path.join(TEST_KEYS_ROOT_DIR, 'repo3')))

        key_list = repo_keys.key_filenames()
        self.assertTrue(key_list is not None)
        self.assertEqual(0, len(key_list))
        
# -- repo cert files tests ----------------------------------------------------------------

class TestRepoCertFiles(unittest.TestCase):

    def setUp(self):
        # Clean up from any previous runs that may have exited abnormally
        if os.path.exists(TEST_CERT_ROOT_DIR):
            shutil.rmtree(TEST_CERT_ROOT_DIR)

    def tearDown(self):
        # Clean up in case the test file was saved in a test
        if os.path.exists(TEST_CERT_ROOT_DIR):
            shutil.rmtree(TEST_CERT_ROOT_DIR)
            
    def test_repo_first_time(self, repoid='repo1'):
        # setup
        repoid = 'repo1'
        ca = 'MY-CA-CERT'
        client = 'MY-CLIENT-KEY_AND_CERT'
        cf = CertFiles(TEST_CERT_ROOT_DIR, repoid)
        cf.update(ca, client)
        capath, clientpath = cf.apply()
        #verify
        rootdir = os.path.join(TEST_CERT_ROOT_DIR, repoid)
        self.assertTrue(os.path.exists(rootdir))
        self.assertEqual(capath, os.path.join(rootdir, CertFiles.CA))
        self.assertEqual(clientpath, os.path.join(rootdir, CertFiles.CLIENT))
        for path, content in ((capath, ca),(clientpath, client)):
            f = open(path)
            pem = f.read()
            f.close()
            self.assertEqual(pem, content)
    
    def test_update(self):
        # setup
        repoid = 'repo1'
        self.test_repo_first_time(repoid)
        ca = 'MY-NEW-CA-CERT'
        client = 'MY-NEW-CLIENT-KEY_AND_CERT'
        cf = CertFiles(TEST_CERT_ROOT_DIR, repoid)
        cf.update(ca, client)
        capath, clientpath = cf.apply()
        #verify
        rootdir = os.path.join(TEST_CERT_ROOT_DIR, repoid)
        self.assertTrue(os.path.exists(rootdir))
        self.assertEqual(capath, os.path.join(rootdir, CertFiles.CA))
        self.assertEqual(clientpath, os.path.join(rootdir, CertFiles.CLIENT))
        self.assertEqual(len(os.listdir(rootdir)), 2)
        for path, content in ((capath, ca),(clientpath, client)):
            f = open(path)
            pem = f.read()
            f.close()
            self.assertEqual(pem, content)
    
    def test_clear_ca(self):
        # setup
        repoid = 'repo1'
        self.test_repo_first_time(repoid)
        ca = None
        client = 'MY-NEW-CLIENT-KEY_AND_CERT'
        cf = CertFiles(TEST_CERT_ROOT_DIR, repoid)
        cf.update(ca, client)
        capath, clientpath = cf.apply()
        #verify
        rootdir = os.path.join(TEST_CERT_ROOT_DIR, repoid)
        self.assertTrue(os.path.exists(rootdir))
        self.assertEqual(clientpath, os.path.join(rootdir, CertFiles.CLIENT))
        self.assertEqual(len(os.listdir(rootdir)), 1)
        f = open(clientpath)
        pem = f.read()
        f.close()
        self.assertEqual(pem, client)
    
    def test_clear_client(self):
        # setup
        repoid = 'repo1'
        self.test_repo_first_time(repoid)
        ca = 'MY-NEW-CA-CERT'
        client = None
        cf = CertFiles(TEST_CERT_ROOT_DIR, repoid)
        cf.update(ca, client)
        capath, clientpath = cf.apply()
        #verify
        rootdir = os.path.join(TEST_CERT_ROOT_DIR, repoid)
        self.assertTrue(os.path.exists(rootdir))
        self.assertEqual(capath, os.path.join(rootdir, CertFiles.CA))
        self.assertEqual(len(os.listdir(rootdir)), 1)
        f = open(capath)
        pem = f.read()
        f.close()
        self.assertEqual(pem, ca)
    
    def test_clear_both(self):
        # setup
        repoid = 'repo1'
        self.test_repo_first_time(repoid)
        ca = None
        client = None
        cf = CertFiles(TEST_CERT_ROOT_DIR, repoid)
        cf.update(ca, client)
        capath, clientpath = cf.apply()
        #verify
        rootdir = os.path.join(TEST_CERT_ROOT_DIR, repoid)
        self.assertFalse(os.path.exists(rootdir))
    

# -- utilities ------------------------------------------------------------------------

def _repo_eq(repo1, repo2):
    """
    Tests the contents of both repos for equality. If they all values match, returns
    True; otherwise False.
    """

    for key in repo1.keys():
        if key not in repo2:
            return False

        # Convert to strings to get around cases where an int is returned
        if str(repo1[key]) != str(repo2[key]):
            print('Repo1 [%s:%s]  Repo2 [%s:%s]' % (key, repo1[key], key, repo2[key]))
            return False

    return True
