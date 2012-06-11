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
import os
import shutil
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.gc_client.lib import repolib
from pulp.gc_client.lib.lock import Lock
from pulp.gc_client.lib.repo_file import MirrorListFile, RepoFile, Repo

# -- constants ------------------------------------------------------------------------

TEST_REPO_FILENAME = '/tmp/TestRepolibFile.repo'
TEST_MIRROR_LIST_FILENAME = '/tmp/TestRepolibFile.mirrorlist'
TEST_KEYS_DIR = '/tmp/TestRepolibFile-keys'
TEST_CERT_DIR = '/tmp/TestRepolibFile-certificates'
CACERT = 'MY-CA-CERTIFICATE'
CLIENTCERT = 'MY-CLIENT-KEY-AND-CERTIFICATE'

# Dict representation of a repo, meant to simulate a normal repo coming in
# from the Pulp server
REPO = {
    'id'        : 'repo-1',
    'display_name'      : 'Repository 1',
}

ENABLED = True

# Lock that doesn't require root privileges
LOCK = Lock('/tmp/test_repolib_lock.pid')

# -- test classes ---------------------------------------------------------------------

class TestRepolib(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        # Clean up from any previous runs that may have exited abnormally
        if os.path.exists(TEST_REPO_FILENAME):
            os.remove(TEST_REPO_FILENAME)

        if os.path.exists(TEST_MIRROR_LIST_FILENAME):
            os.remove(TEST_MIRROR_LIST_FILENAME)

        if os.path.exists(TEST_KEYS_DIR):
            shutil.rmtree(TEST_KEYS_DIR)
            
        if os.path.exists(TEST_CERT_DIR):
            shutil.rmtree(TEST_CERT_DIR)


    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)
        # Clean up in case the test file was saved in a test
        if os.path.exists(TEST_REPO_FILENAME):
            os.remove(TEST_REPO_FILENAME)

        if os.path.exists(TEST_MIRROR_LIST_FILENAME):
            os.remove(TEST_MIRROR_LIST_FILENAME)

        if os.path.exists(TEST_KEYS_DIR):
            shutil.rmtree(TEST_KEYS_DIR)

        if os.path.exists(TEST_CERT_DIR):
            shutil.rmtree(TEST_CERT_DIR)

    # -- bind tests ------------------------------------------------------------------

    def test_bind_new_file(self):
        '''
        Tests binding a repo when the underlying .repo file does not exist.
        '''

        # Test
        url_list = ['http://pulpserver']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, {}, CACERT, CLIENTCERT, ENABLED, LOCK)

        # Verify
        self.assertTrue(os.path.exists(TEST_REPO_FILENAME))
        self.assertTrue(not os.path.exists(TEST_MIRROR_LIST_FILENAME))

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        self.assertEqual(1, len(repo_file.all_repos()))

        loaded = repo_file.get_repo(REPO['id'])
        self.assertTrue(loaded is not None)
        self.assertEqual(loaded['name'], REPO['display_name'])
        self.assertTrue(loaded['enabled'])
        self.assertEqual(loaded['gpgcheck'], '0')
        self.assertEqual(loaded['gpgkey'], None)

        self.assertEqual(loaded['baseurl'], url_list[0])
        self.assertTrue('mirrorlist' not in loaded)
        
        path = loaded['sslcacert']
        f = open(path)
        content = f.read()
        f.close()
        self.assertEqual(CACERT, content)
        path = loaded['sslclientcert']
        f = open(path)
        content = f.read()
        f.close()
        self.assertEqual(CLIENTCERT, content)
        self.assertTrue(loaded['sslverify'], '1')

    def test_bind_existing_file(self):
        '''
        Tests binding a new repo when the underlying file exists and has repos in it
        (the existing repo shouldn't be deleted).
        '''

        # Setup
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.add_repo(Repo('existing-repo-1'))
        repo_file.save()

        # Test
        url_list = ['http://pulpserver']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, {}, None, None, ENABLED, LOCK)

        # Verify
        self.assertTrue(os.path.exists(TEST_REPO_FILENAME))

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        self.assertEqual(2, len(repo_file.all_repos()))

    def test_bind_update_repo(self):
        '''
        Tests calling bind on an existing repo with new repo data. The host URL and key data
        remain unchanged.
        '''

        # Setup
        url_list = ['http://pulp1', 'http://pulp2']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, None, None, None, ENABLED, LOCK)

        # Test
        updated_repo = dict(REPO)
        updated_repo['display_name'] = 'Updated'

        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], updated_repo, None, None, None, None, ENABLED, LOCK)

        # Verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        loaded = repo_file.get_repo(REPO['id'])
        self.assertEqual(loaded['name'], updated_repo['display_name'])

    def test_bind_update_host_urls(self):
        '''
        Tests calling bind on an existing repo with new repo data. This test will test
        the more complex case where a mirror list existed in the original repo but is
        not necessary in the updated repo.
        '''

        # Setup
        url_list = ['http://pulp1', 'http://pulp2']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, None, None, None, ENABLED, LOCK)

        self.assertTrue(os.path.exists(TEST_MIRROR_LIST_FILENAME))

        # Test
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], None, ['http://pulpx'], None, None, None, ENABLED, LOCK)

        # Verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        loaded = repo_file.get_repo(REPO['id'])
        self.assertEqual(loaded['baseurl'], 'http://pulpx')

        self.assertTrue(not os.path.exists(TEST_MIRROR_LIST_FILENAME))

    def test_bind_host_urls_one_to_many(self):
        '''
        Tests that changing from a single URL to many properly updates the baseurl and
        mirrorlist entries of the repo.
        '''

        # Setup
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, ['https://pulpx'], None, None, None, ENABLED, LOCK)

        # Test
        url_list = ['http://pulp1', 'http://pulp2']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, None, None, None, ENABLED, LOCK)

        # Verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        loaded = repo_file.get_repo(REPO['id'])
        self.assertTrue('baseurl' not in loaded)
        self.assertTrue('mirrorlist' in loaded)

    def test_bind_host_urls_many_to_one(self):
        '''
        Tests that changing from multiple URLs (mirrorlist usage) to a single URL
        properly sets the repo metadata.
        '''
        # Setup
        url_list = ['http://pulp1', 'http://pulp2']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, None, None, None, ENABLED, LOCK)

        # Test
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, ['http://pulpx'], None, None, None, ENABLED, LOCK)

        # Verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        loaded = repo_file.get_repo(REPO['id'])
        self.assertTrue('baseurl' in loaded)
        self.assertTrue('mirrorlist' not in loaded)

    def test_bind_update_keys(self):
        '''
        Tests changing the GPG keys on a previously bound repo.
        '''

        # Setup
        keys = {'key1' : 'KEY1', 'key2' : 'KEY2'}
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, ['http://pulp'], keys, None, None, ENABLED, LOCK)

        # Test
        new_keys = {'key1' : 'KEYX'}
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], None, None, new_keys, None, None, ENABLED, LOCK)

        # Verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        loaded = repo_file.get_repo(REPO['id'])
        self.assertEqual(loaded['gpgcheck'], '1')
        self.assertEqual(1, len(loaded['gpgkey'].split('\n')))
        self.assertEqual(1, len(os.listdir(os.path.join(TEST_KEYS_DIR, REPO['id']))))

        key_file = open(loaded['gpgkey'].split('\n')[0][5:], 'r')
        contents = key_file.read()
        key_file.close()

        self.assertEqual(contents, 'KEYX')

    def test_bind_update_remove_keys(self):
        '''
        Tests that updating a previously bound repo by removing its keys correctly
        configures the repo and deletes the key files.
        '''

        # Setup
        keys = {'key1' : 'KEY1', 'key2' : 'KEY2'}
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, ['http://pulp'], keys, None, None, ENABLED, LOCK)

        # Test
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], None, None, {}, None, None, ENABLED, LOCK)

        # Verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        loaded = repo_file.get_repo(REPO['id'])
        self.assertEqual(loaded['gpgcheck'], '0')
        self.assertEqual(loaded['gpgkey'], None)
        self.assertTrue(not os.path.exists(os.path.join(TEST_KEYS_DIR, REPO['id'])))
        
    def test_clear_cacert(self):
        # setup
        repolib.bind(
            TEST_REPO_FILENAME,
            TEST_MIRROR_LIST_FILENAME,
            TEST_KEYS_DIR,
            TEST_CERT_DIR,
            REPO['id'],
            REPO,
            ['http://pulp'],
            [], 
            CACERT, 
            CLIENTCERT,
            ENABLED,
            LOCK)
        repolib.bind(
            TEST_REPO_FILENAME,
            TEST_MIRROR_LIST_FILENAME,
            TEST_KEYS_DIR,
            TEST_CERT_DIR,
            REPO['id'],
            REPO,
            ['http://pulp'],
            [], 
            None, 
            CLIENTCERT,
            ENABLED,
            LOCK)
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()
        loaded = repo_file.get_repo(REPO['id'])
        # verify
        certdir = os.path.join(TEST_CERT_DIR, REPO['id'])
        self.assertTrue(len(os.listdir(certdir)), 1)
        path = loaded['sslclientcert']
        f = open(path)
        content = f.read()
        f.close()
        self.assertEqual(CLIENTCERT, content)
        self.assertTrue(loaded['sslverify'], '0')

    def test_clear_clientcert(self):
        # setup
        repolib.bind(
            TEST_REPO_FILENAME,
            TEST_MIRROR_LIST_FILENAME,
            TEST_KEYS_DIR,
            TEST_CERT_DIR,
            REPO['id'],
            REPO,
            ['http://pulp'],
            [], 
            CACERT, 
            CLIENTCERT,
            ENABLED,
            LOCK)
        repolib.bind(
            TEST_REPO_FILENAME,
            TEST_MIRROR_LIST_FILENAME,
            TEST_KEYS_DIR,
            TEST_CERT_DIR,
            REPO['id'],
            REPO,
            ['http://pulp'],
            [], 
            CACERT, 
            None,
            ENABLED,
            LOCK)
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()
        loaded = repo_file.get_repo(REPO['id'])
        # verify
        certdir = os.path.join(TEST_CERT_DIR, REPO['id'])
        self.assertTrue(len(os.listdir(certdir)), 1)
        path = loaded['sslcacert']
        f = open(path)
        content = f.read()
        f.close()
        self.assertEqual(CACERT, content)
        self.assertTrue(loaded['sslverify'], '1')
        
    def test_update_cacert(self):
        # setup
        NEWCACERT = 'THE-NEW-CA-CERT'
        repolib.bind(
            TEST_REPO_FILENAME,
            TEST_MIRROR_LIST_FILENAME,
            TEST_KEYS_DIR,
            TEST_CERT_DIR,
            REPO['id'],
            REPO,
            ['http://pulp'],
            [], 
            CACERT, 
            CLIENTCERT,
            ENABLED,
            LOCK)
        repolib.bind(
            TEST_REPO_FILENAME,
            TEST_MIRROR_LIST_FILENAME,
            TEST_KEYS_DIR,
            TEST_CERT_DIR,
            REPO['id'],
            REPO,
            ['http://pulp'],
            [], 
            NEWCACERT, 
            CLIENTCERT,
            ENABLED,
            LOCK)
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()
        loaded = repo_file.get_repo(REPO['id'])
        # verify
        certdir = os.path.join(TEST_CERT_DIR, REPO['id'])
        self.assertTrue(len(os.listdir(certdir)), 2)
        path = loaded['sslcacert']
        f = open(path)
        content = f.read()
        f.close()
        self.assertEqual(NEWCACERT, content)
        path = loaded['sslclientcert']
        f = open(path)
        content = f.read()
        f.close()
        self.assertEqual(CLIENTCERT, content)
        self.assertTrue(loaded['sslverify'], '1')
        
    def test_update_clientcert(self):
        # setup
        NEWCLIENTCRT = 'THE-NEW-CLIENT-CERT'
        repolib.bind(
            TEST_REPO_FILENAME,
            TEST_MIRROR_LIST_FILENAME,
            TEST_KEYS_DIR,
            TEST_CERT_DIR,
            REPO['id'],
            REPO,
            ['http://pulp'],
            [], 
            CACERT, 
            CLIENTCERT,
            ENABLED,
            LOCK)
        repolib.bind(
            TEST_REPO_FILENAME,
            TEST_MIRROR_LIST_FILENAME,
            TEST_KEYS_DIR,
            TEST_CERT_DIR,
            REPO['id'],
            REPO,
            ['http://pulp'], 
            [],
            CACERT, 
            NEWCLIENTCRT,
            ENABLED,
            LOCK)
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()
        loaded = repo_file.get_repo(REPO['id'])
        # verify
        certdir = os.path.join(TEST_CERT_DIR, REPO['id'])
        self.assertTrue(len(os.listdir(certdir)), 2)
        path = loaded['sslcacert']
        f = open(path)
        content = f.read()
        f.close()
        self.assertEqual(CACERT, content)
        path = loaded['sslclientcert']
        f = open(path)
        content = f.read()
        f.close()
        self.assertEqual(NEWCLIENTCRT, content)
        self.assertTrue(loaded['sslverify'], '1')

    def test_bind_single_url(self):
        '''
        Tests that binding with a single URL will produce a baseurl in the repo.
        '''

        # Test
        url_list = ['http://pulpserver']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, {}, None, None, ENABLED, LOCK)

        # Verify
        self.assertTrue(os.path.exists(TEST_REPO_FILENAME))
        self.assertTrue(not os.path.exists(TEST_MIRROR_LIST_FILENAME))

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        loaded = repo_file.get_repo(REPO['id'])
        self.assertEqual(loaded['baseurl'], url_list[0])
        self.assertTrue('mirrorlist' not in loaded)

    def test_bind_multiple_url(self):
        '''
        Tests that binding with a list of URLs will produce a mirror list and the
        correct mirrorlist entry in the repo entry.
        '''

        # Test
        url_list = ['http://pulpserver', 'http://otherserver']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, {}, None, None, ENABLED, LOCK)

        # Verify
        self.assertTrue(os.path.exists(TEST_REPO_FILENAME))
        self.assertTrue(os.path.exists(TEST_MIRROR_LIST_FILENAME))

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        loaded = repo_file.get_repo(REPO['id'])
        self.assertTrue('baseurl' not in loaded)
        self.assertEqual(loaded['mirrorlist'], 'file:' + TEST_MIRROR_LIST_FILENAME)

        mirror_list_file = MirrorListFile(TEST_MIRROR_LIST_FILENAME)
        mirror_list_file.load()

        self.assertEqual(mirror_list_file.entries[0], 'http://pulpserver')
        self.assertEqual(mirror_list_file.entries[1], 'http://otherserver')

    def test_bind_multiple_keys(self):
        '''
        Tests that binding with multiple key URLs correctly stores the repo entry.
        '''

        # Test
        url_list = ['http://pulpserver']
        keys = {'key1' : 'KEY1', 'key2' : 'KEY2'}

        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, keys, None, None, ENABLED, LOCK)

        # Verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        loaded = repo_file.get_repo(REPO['id'])
        self.assertEqual(loaded['gpgcheck'], '1')
        self.assertEqual(2, len(loaded['gpgkey'].split('\n')))
        self.assertEqual(2, len(os.listdir(os.path.join(TEST_KEYS_DIR, REPO['id']))))

    # -- unbind tests ------------------------------------------------------------------

    def test_unbind_repo_exists(self):
        '''
        Tests the normal case of unbinding a repo that exists in the repo file.
        '''

        # Setup
        repoid = 'test-unbind-repo'
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.add_repo(Repo(repoid))
        repo_file.save()

        # Test
        repolib.unbind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, 'test-unbind-repo', LOCK)

        # verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load(allow_missing=False) # the file should still be there, so error if it doesn't

        self.assertEqual(0, len(repo_file.all_repos()))
        
        certdir = os.path.join(TEST_CERT_DIR, repoid)
        self.assertFalse(os.path.exists(certdir))

    def test_unbind_repo_with_mirrorlist(self):
        '''
        Tests that unbinding a repo that had a mirror list deletes the mirror list
        file.
        '''

        # Setup
        url_list = ['http://pulp1', 'http://pulp2', 'http://pulp3']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, {}, None, None, ENABLED, LOCK)
        self.assertTrue(os.path.exists(TEST_MIRROR_LIST_FILENAME))

        # Test
        repolib.unbind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], LOCK)

        # Verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()
        self.assertEqual(0, len(repo_file.all_repos()))

        self.assertTrue(not os.path.exists(TEST_MIRROR_LIST_FILENAME))

    def test_unbind_repo_with_keys(self):
        '''
        Tests that unbinding a repo that had GPG keys deletes the key files.
        '''

        # Setup
        url_list = ['http://pulp1']
        keys = {'key1' : 'KEY1', 'key2' : 'KEY2'}

        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, url_list, keys, None, None, ENABLED, LOCK)

        self.assertTrue(os.path.exists(os.path.join(TEST_KEYS_DIR, REPO['id'])))

        # Test
        repolib.unbind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], LOCK)

        # Verify
        self.assertTrue(not os.path.exists(os.path.join(TEST_KEYS_DIR, REPO['id'])))

    def test_unbind_missing_file(self):
        '''
        Tests that calling unbind in the case where the underlying .repo file has been
        deleted does not result in an error.
        '''

        # Setup
        self.assertTrue(not os.path.exists(TEST_REPO_FILENAME))

        # Test
        repolib.unbind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], LOCK)

        # Verify
        # The above shouldn't throw an error

    def test_unbind_missing_repo(self):
        '''
        Tests that calling unbind on a repo that isn't bound does not result in
        an error.
        '''

        # Setup
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, REPO['id'], REPO, ['http://pulp'], {}, None, None, ENABLED, LOCK)

        # Test
        repolib.unbind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, TEST_KEYS_DIR, TEST_CERT_DIR, 'fake-repo', LOCK)

        # Verify
        # The above shouldn't throw an error; the net effect is still that the repo is unbound
