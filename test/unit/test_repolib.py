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
import os
import sys
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import pulp.client.repolib as repolib
from pulp.client.repo_file import MirrorListFile, RepoFile, Repo

# -- constants ------------------------------------------------------------------------

TEST_REPO_FILENAME = '/tmp/TestRepolibFile.repo'
TEST_MIRROR_LIST_FILENAME = '/tmp/TestRepolibFile.mirrorlist'

# Dict representation of a repo, meant to simulate a normal repo coming in
# from the Pulp server
REPO = {
    'id'      : 'repo-1',
    'name'    : 'Repository 1',
    'publish' : 'True',
}

# Lock that doesn't require root privileges
LOCK = repolib.ActionLock('/tmp/test_repolib_lock.pid')

# -- test classes ---------------------------------------------------------------------

class TestRepolib(unittest.TestCase):

    def setUp(self):
        # Clean up from any previous runs that may have exited abnormally
        if os.path.exists(TEST_REPO_FILENAME):
            os.remove(TEST_REPO_FILENAME)

        if os.path.exists(TEST_MIRROR_LIST_FILENAME):
            os.remove(TEST_MIRROR_LIST_FILENAME)

    def tearDown(self):
        # Clean up in case the test file was saved in a test
        if os.path.exists(TEST_REPO_FILENAME):
            os.remove(TEST_REPO_FILENAME)

        if os.path.exists(TEST_MIRROR_LIST_FILENAME):
            os.remove(TEST_MIRROR_LIST_FILENAME)

    # -- bind tests ------------------------------------------------------------------

    def test_bind_new_file(self):
        '''
        Tests binding a repo when the underlying .repo file does not exist.
        '''

        # Test
        url_list = ['http://pulpserver']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, REPO, url_list, LOCK)

        # Verify
        self.assertTrue(os.path.exists(TEST_REPO_FILENAME))
        self.assertTrue(not os.path.exists(TEST_MIRROR_LIST_FILENAME))

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        self.assertEqual(1, len(repo_file.all_repos()))

        loaded = repo_file.get_repo(REPO['id'])
        self.assertTrue(loaded is not None)
        self.assertEqual(loaded['name'], REPO['name'])
        self.assertTrue(loaded['enabled'])

        self.assertEqual(loaded['baseurl'], url_list[0])
        self.assertTrue('mirrorlist' not in loaded)

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
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, REPO, url_list, LOCK)

        # Verify
        self.assertTrue(os.path.exists(TEST_REPO_FILENAME))

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        self.assertEqual(2, len(repo_file.all_repos()))

    def test_bind_single_url(self):
        '''
        Tests that binding with a single URL will produce a baseurl in the repo.
        '''

        # Test
        url_list = ['http://pulpserver']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, REPO, url_list, LOCK)

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
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, REPO, url_list, LOCK)

        # Verify
        self.assertTrue(os.path.exists(TEST_REPO_FILENAME))
        self.assertTrue(os.path.exists(TEST_MIRROR_LIST_FILENAME))

        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()

        loaded = repo_file.get_repo(REPO['id'])
        self.assertTrue('baseurl' not in loaded)
        self.assertEqual(loaded['mirrorlist'], TEST_MIRROR_LIST_FILENAME)

        mirror_list_file = MirrorListFile(TEST_MIRROR_LIST_FILENAME)
        mirror_list_file.load()

        self.assertEqual(mirror_list_file.entries[0], 'http://pulpserver')
        self.assertEqual(mirror_list_file.entries[1], 'http://otherserver')

    # -- unbind tests ------------------------------------------------------------------

    def test_unbind_repo_exists(self):
        '''
        Tests the normal case of unbinding a repo that exists in the repo file.
        '''

        # Setup
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.add_repo(Repo('test-unbind-repo'))
        repo_file.save()

        # Test
        repolib.unbind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, 'test-unbind-repo', LOCK)

        # verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load(allow_missing=False) # the file should still be there, so error if it doesn't

        self.assertEqual(0, len(repo_file.all_repos()))

    def test_unbind_repo_with_mirrorlist(self):
        '''
        Tests that unbinding a repo that had a mirror list deletes the mirror list
        file.
        '''

        # Setup
        url_list = ['http://pulp1', 'http://pulp2', 'http://pulp3']
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, REPO, url_list, LOCK)
        self.assertTrue(os.path.exists(TEST_MIRROR_LIST_FILENAME))

        # Test
        repolib.unbind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, REPO['id'], LOCK)

        # Verify
        repo_file = RepoFile(TEST_REPO_FILENAME)
        repo_file.load()
        self.assertEqual(0, len(repo_file.all_repos()))

        self.assertTrue(not os.path.exists(TEST_MIRROR_LIST_FILENAME))

    def test_unbind_missing_file(self):
        '''
        Tests that calling unbind in the case where the underlying .repo file has been
        deleted does not result in an error.
        '''

        # Setup
        self.assertTrue(not os.path.exists(TEST_REPO_FILENAME))

        # Test
        repolib.unbind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, REPO, LOCK)

        # Verify
        # The above shouldn't throw an error

    def test_unbind_missing_repo(self):
        '''
        Tests that calling unbind on a repo that isn't bound does not result in
        an error.
        '''

        # Setup
        repolib.bind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, REPO, ['http://pulp'], LOCK)

        # Test
        repolib.unbind(TEST_REPO_FILENAME, TEST_MIRROR_LIST_FILENAME, 'fake-repo', LOCK)

        # Verify
        # The above shouldn't throw an error; the net effect is still that the repo is unbound