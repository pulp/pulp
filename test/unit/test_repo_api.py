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

# Python
import random
import logging
import stat
import sys
import os
import time
import unittest
import shutil

import mock

try:
    import json
except ImportError:
    import simplejson as json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import pymongo.json_util

from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.repo_auth.protected_repo_utils import ProtectedRepoUtils
from pulp.server.api import repo, repo_sync, consumer
from pulp.server.api.package import PackageHasReferences
from pulp.server.api.keystore import KeyStore
from pulp.server.db.model import Delta
from pulp.server.db.model import Consumer
from pulp.server.db.model import persistence
from pulp.server.tasking.task import Task, task_running
from pulp.server.tasking.exception import ConflictingOperationException
from pulp.server.util import random_string
from pulp.server.util import get_rpm_information, get_repomd_filetype_dump
from pulp.client.lib.utils import generatePakageProfile
from pulp.server.util import top_repos_location
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server import constants
from pulp.server.exceptions import PulpException

logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

CERTS_DIR = '/tmp/test_repo_api/repos'

KEY = """
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

CERTIFICATE = """
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

BUNDLE = ''.join((KEY,CERTIFICATE))


class TestRepoApi(testutil.PulpAsyncTest):

    def clean(self):
        testutil.PulpAsyncTest.clean(self)
        persistence.TaskSnapshot.get_collection().remove()
        persistence.TaskHistory.get_collection().remove()

        if os.path.exists(CERTS_DIR):
            shutil.rmtree(CERTS_DIR)

        protected_repo_listings_file = self.config.get('repos', 'protected_repo_listing_file')
        if os.path.exists(protected_repo_listings_file):
            os.remove(protected_repo_listings_file)

        shutil.rmtree(constants.LOCAL_STORAGE, ignore_errors=True)

        sn = SerialNumber()
        sn.reset()

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.config.set('repos', 'cert_location', CERTS_DIR)

        self.repo_cert_utils = RepoCertUtils(self.config)
        self.protected_repo_utils = ProtectedRepoUtils(self.config)

    def deleteRepos(self):
        repo.RepoApi().clean()
        consumer.ConsumerApi().clean()

    def test_repo_create(self, repo_id = 'some-repo-id'):
        repo = self.repo_api.create(repo_id, 'some name',
            'i386', 'http://example.com')
        assert(repo is not None)

    def test_repo_create_with_whitespace(self):
        repo_id = "test  whitespace"
        self.assertRaises(PulpException, self.repo_api.create, repo_id, 'valid-name', 'bad-arch')
        self.assertRaises(PulpException, self.repo_api.create, 'valid-id', 'valid-name', 'bad-arch', relative_path=repo_id)

    def test_repo_clone_with_whitespace(self):
        clone_id = "test  whitespace"
        repo = self.repo_api.create('valid-id', 'some name',
            'i386', 'http://example.com')
        self.assertRaises(PulpException, repo_sync.clone, 'valid-id', clone_id, clone_id)
        self.assertRaises(PulpException, repo_sync.clone, 'valid-id', 'valid-clone-id', 'valid-clone-id', relative_path=clone_id)

    def test_i18n_repo_relative_path(self):
        repo_id = u'\u0938\u093e\u092f\u0932\u0940'
        repo = self.repo_api.create(repo_id, 'some name', 'i386', 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/',
                                    relative_path=repo_id)
        assert(repo is not None)
        repo_sync._sync(repo_id)

    def test_repo_create_with_notes(self, repo_id = 'some-repo-with-notes-id'):
        notes = {'key':'value','k':'v'}
        repo = self.repo_api.create(repo_id, 'some name',
            'i386', 'http://example.com', notes=notes)
        assert(repo is not None)
        assert(repo['notes'] == notes)

    def test_repo_create_feedless(self, repo_id = 'some-id-no-feed'):
        repo = self.repo_api.create(repo_id, 'some name', 'i386')
        assert(repo is not None)

    def test_repo_create_bad_arch(self, repo_id = 'valid-id'):
        self.assertRaises(PulpException, self.repo_api.create, repo_id, 'valid-name', 'bad-arch')

    def test_repo_create_with_feed_certs(self, repo_id = 'test_feed_cert'):
        '''
        Tests that creating a repo specifying a feed cert bundle correctly writes them
        to disk.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'cert' : BUNDLE}

        # Test
        self.repo_api.create(repo_id, 'Test Feed Cert', 'noarch', feed_cert_data=bundle)

        # Verify
        #   repo_cert_utils will verify the contents are correct, just make sure
        #   the certs are present on disk
        repo_cert_dir = self.repo_cert_utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        repo_certs = os.listdir(repo_cert_dir)
        self.assertEqual(2, len(repo_certs))
        self.assertEqual(0, len([fn for fn in repo_certs if not fn.startswith('feed')]))

    def test_repo_create_with_consumer_certs(self, repo_id = 'test_consumer_cert'):
        '''
        Tests that creating a repo specifying a consumer cert bundle correctly writes them
        to disk.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'cert' : BUNDLE}

        # Test
        self.repo_api.create(repo_id, 'Test Consumer Cert', 'noarch', consumer_cert_data=bundle)

        # Verify
        repo_cert_dir = self.repo_cert_utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        repo_certs = os.listdir(repo_cert_dir)
        self.assertEqual(2, len(repo_certs))
        self.assertEqual(0, len([fn for fn in repo_certs if not fn.startswith('consumer')]))

        protected_repo_listings_file = self.config.get('repos', 'protected_repo_listing_file')
        self.assertTrue(os.path.exists(protected_repo_listings_file))
        protected_repos = self.protected_repo_utils.read_protected_repo_listings()
        self.assertTrue(repo_id in protected_repos.values())

    def test_repo_create_with_both_certs(self, repo_id = 'test_both_cert'):
        '''
        Tests that creating a repo specifying both consumer and feed bundles correctly
        write them to disk
        '''

        # Setup
        feed_bundle = {'ca' : 'FOO', 'key' : KEY, 'cert' : CERTIFICATE}
        consumer_bundle = {'ca' : 'WOMBAT', 'cert' : BUNDLE}

        # Test
        r = self.repo_api.create(repo_id, 'Test Feed Cert', 'noarch', feed_cert_data=feed_bundle,
                         consumer_cert_data=consumer_bundle)

        # Verify
        repo_cert_dir = self.repo_cert_utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        repo_certs = os.listdir(repo_cert_dir)
        self.assertEqual(4, len(repo_certs))
        self.assertEqual(2, len([fn for fn in repo_certs if fn.startswith('feed')]))
        self.assertEqual(2, len([fn for fn in repo_certs if fn.startswith('consumer')]))

        protected_repo_listings_file = self.config.get('repos', 'protected_repo_listing_file')
        self.assertTrue(os.path.exists(protected_repo_listings_file))
        protected_repos = self.protected_repo_utils.read_protected_repo_listings()
        self.assertTrue(repo_id in protected_repos.values())
        
        path = r['feed_cert']
        f = open(path)
        cert = f.read()
        f.close()
        self.assertTrue(cert.strip(), BUNDLE.strip())
        path = r['consumer_cert']
        f = open(path)
        cert = f.read()
        f.close()
        self.assertTrue(cert.strip(), BUNDLE.strip())

    def test_repo_create_conflicting_relative_path(self, repo_id = 'existing'):
        """
        Tests that creating a repository whose relative path conflicts with an existing repository raises the correct error.
        """

        # Setup
        self.repo_api.create('existing', 'Existing', 'noarch', relative_path='foo/bar')

        # Test
        self.assertRaises(PulpException, self.repo_api.create, 'proposed', 'Proposed', 'noarch', relative_path='foo/bar/baz')

    def test_repo_update_with_feed_certs(self, repo_id = 'test_feed_cert'):
        '''
        Tests that updating a repo by adding feed certs properly stores the certs.
        '''

        # Setup
        self.repo_api.create(repo_id, 'Test Feed Cert', 'noarch')

        # Test
        bundle = {'ca' : 'FOO', 'cert' : BUNDLE}
        self.repo_api.update(repo_id, {'feed_cert_data' : bundle})

        # Verify
        repo_cert_dir = self.repo_cert_utils._repo_cert_directory(repo_id)
        self.assertTrue(os.path.exists(repo_cert_dir))

        repo_certs = os.listdir(repo_cert_dir)
        self.assertEqual(2, len(repo_certs))
        self.assertEqual(0, len([fn for fn in repo_certs if not fn.startswith('feed')]))


    def test_repo_delete_with_feed_certs(self, repo_id = 'test_feed_cert'):
        '''
        Tests that deleting a repo with feed certs assigned properly removes the certs.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'key' : KEY, 'cert' : CERTIFICATE}
        self.repo_api.create(repo_id, 'Test Feed Cert', 'noarch', feed_cert_data=bundle)

        # Test
        self.repo_api.delete(repo_id)

        # Verify
        repo_cert_dir = self.repo_cert_utils._repo_cert_directory(repo_id)
        self.assertTrue(not os.path.exists(repo_cert_dir))

    def test_repo_delete_with_consumer_certs(self, repo_id = 'test_consumer_cert'):
        '''
        Tests that deleting a repo with consumer certs properly cleans them up from the
        protected repo listing.
        '''

        # Setup
        bundle = {'ca' : 'FOO', 'key' : KEY, 'cert' : CERTIFICATE}
        self.repo_api.create(repo_id, 'Test Consumer Cert', 'noarch', consumer_cert_data=bundle)

        # Test
        self.repo_api.delete(repo_id)

        # Verify

        #   repo_cert_utils will verify the contents are correct, just make sure
        #   the certs are present on disk
        repo_cert_dir = self.repo_cert_utils._repo_cert_directory(repo_id)
        self.assertTrue(not os.path.exists(repo_cert_dir))

        protected_repo_listings_file = self.config.get('repos', 'protected_repo_listing_file')
        self.assertTrue(os.path.exists(protected_repo_listings_file))
        protected_repos = self.protected_repo_utils.read_protected_repo_listings()
        self.assertTrue(repo_id not in protected_repos.values())

    def test_repo_duplicate(self, repo_id = 'some-id'):
        name = 'some name'
        arch = 'i386'
        feed = 'http://example.com'
        repo = self.repo_api.create(repo_id, name, arch, feed)
        try:
            repo = self.repo_api.create(repo_id, name, arch, feed)
            raise Exception, 'Duplicate allowed'
        except:
            pass

    def test_feed_types(self, repo_id = 'some-id'):
        failed = False
        try:
            repo = self.repo_api.create(repo_id, 'some name',
                'i386', 'foo://example.com/')
        except:
            failed = True
        assert(failed)

        try:
            repo = self.repo_api.create(repo_id, 'some name',
                'i386', 'blippybloopyfoo')
        except:
            failed = True
        assert(failed)


        repo = self.repo_api.create(repo_id, 'some name',
            'i386', 'http://example.com')
        assert(repo is not None)
        assert(repo['source']['type'] == 'remote')

    def test_clean(self, repo_id = 'some-id'):
        repo = self.repo_api.create(repo_id, 'some name',
            'i386', 'http://example.com')
        self.repo_api.clean()
        repos = self.repo_api.repositories()
        assert(len(repos) == 0)

    def test_delete(self, id = 'some-id'):
        repo = self.repo_api.create(id, 'some name', 'i386', 'http://example.com')
        repo = self.repo_api.repository(id)
        assert(repo is not None)
        self.repo_api.delete(id=id)
        repo = self.repo_api.repository(id)
        assert(repo is None)

    def test_delete_non_existing_clone_id(self, id = 'some-id'):
        repo = self.repo_api.create(id, 'some name', 'i386', 'http://example.com')
        repo = self.repo_api.repository(id)
        assert(repo is not None)
        clone_ids = repo['clone_ids']
        clone_ids.append("non_existing_clone_id")
        repo['clone_ids'] = clone_ids
        self.repo_api.collection.save(repo, safe=True)
        self.repo_api.delete(id=id)
        repo = self.repo_api.repository(id)
        assert(repo is None)

    def test_delete_feedless(self, id = 'some-id-no-feed'):
        repo = self.repo_api.create(id, 'some name', 'i386')
        repo = self.repo_api.repository(id)
        assert(repo is not None)
        self.repo_api.delete(id=id)
        repo = self.repo_api.repository(id)
        assert(repo is None)

    def test_repositories(self, repo_id = 'some-id'):
        repo = self.repo_api.create(repo_id, 'some name',
            'i386', 'http://example.com')

        # list all the repos
        repos = self.repo_api.repositories()
        found = False
        assert(len(repos) > 0)
        for r in repos:
            ## TODO: See if we can get dot notation here on id field
            if (r['id'] == repo_id):
                found = True

        assert(found)

    def test_repository(self, id = 'some-id'):
        repo = self.repo_api.create(id, 'some name', \
            'i386', 'http://example.com')

        found = self.repo_api.repository(id)
        assert(found is not None)
        assert(found['id'] == id)

    def test_repository_with_groupid(self, id = 'some-id'):
        repo = self.repo_api.create(id, 'some name', \
            'i386', 'http://example.com/mypath', groupid=["testgroup"])
        found = self.repo_api.repository(id)
        assert(found is not None)
        assert(found['id'] == id)
        assert(found['groupid'] == ["testgroup"])

    def test_repository_with_relativepath(self, id = 'some-id-mypath'):
        repo = self.repo_api.create('some-id-mypath', 'some name', \
            'i386', 'http://example.com/mypath', relative_path="/mypath/")
        found = self.repo_api.repository(id)
        assert(found is not None)
        assert(found['id'] == id)
        assert(found['relative_path'] == "mypath")

        # default path
        repo = self.repo_api.create('some-id-default-path', 'some name', \
            'i386', 'http://example.com/test/mypath')
        found = self.repo_api.repository('some-id-default-path')
        assert(found is not None)
        assert(found['id'] == 'some-id-default-path')
        assert(found['relative_path'] == "test/mypath")


    def test_repo_packages(self):
        repo = self.repo_api.create('some-id', 'some name', \
            'i386', 'http://example.com')
        p = testutil.create_package(self.package_api, 'test_repo_packages')
        self.repo_api.add_package(repo["id"], [p['id']])
        for i in range(10):
            package = testutil.create_package(self.package_api, random_string())
            self.repo_api.add_package(repo["id"], [package['id']])

        found = self.repo_api.repository('some-id')
        packages = found['packages']
        assert(packages is not None)
        assert(p['id'] in packages)

    def test_repo_package_count(self):
        repo = self.repo_api.create('some-id', 'some name', \
            'i386', 'http://example.com')
        num_packages = 50
        package = None
        for i in range(num_packages):
            package = testutil.create_package(self.package_api, random_string(), filename=random_string())
            self.repo_api.add_package(repo["id"], [package['id']])

        count = self.repo_api.package_count('some-id')
        self.assertTrue(num_packages == count)
        self.repo_api.remove_package('some-id', package)
        count = self.repo_api.package_count('some-id')
        self.assertTrue(count == (num_packages - 1))


    def test_repo_erratum(self):
        repo = self.repo_api.create('some-id', 'some name', \
            'i386', 'http://example.com')
        id = 'test_errata_id_1'
        title = 'test_errata_title_1'
        description = 'test_errata_description_1'
        version = '1.0'
        release = '0'
        type = 'bugfix'
        test_errata_1 = self.errata_api.create(id, title, description, version, release, type)

        self.assertTrue(test_errata_1 is not None)
        self.repo_api.add_erratum(repo['id'], test_errata_1['id'])

        errata = self.repo_api.errata('some-id', types=['bugfix'])
        self.assertTrue(len(errata) == 1)

        self.repo_api.delete_erratum(repo['id'], test_errata_1['id'])

        errata = self.repo_api.errata('some-id', types=['bugfix'])
        self.assertTrue(len(errata) == 0)


    def test_repo_update(self, id = 'fedora'):
        relativepath = 'f11/i386'
        feed = 'http://abc.com/%s' % relativepath
        repo = self.repo_api.create(id, 'Fedora', 'noarch', feed=feed)

        try:
            d = dict(feed='http://xyz.com/my/new/path')
            repo = self.repo_api.update(id, d)
            self.assertTrue(False, 'should fail')
        except:
            pass

        try:
            d = dict(relative_path='/f11/i386')
            repo = self.repo_api.update(id, d)
            self.assertTrue(True, 'should Pass')
        except:
            pass

    def test_repo_errata(self):
        repo = self.repo_api.create('some-id', 'some name', \
            'i386', 'http://example.com')
        id = 'test_errata_id_1'
        title = 'test_errata_title_1'
        description = 'test_errata_description_1'
        version = '1.0'
        release = '0'
        type = 'bugfix'
        test_errata_1 = self.errata_api.create(id, title, description, version, release, type)
        self.assertTrue(test_errata_1 is not None)

        id = 'test_errata_id_2'
        title = 'test_errata_title_2'
        description = 'test_errata_description_2'
        version = '1.0'
        release = '0'
        type = 'bugfix'
        test_errata_2 = self.errata_api.create(id, title, description, version, release, type)
        self.assertTrue(test_errata_2 is not None)
        self.repo_api.add_errata(repo['id'], [test_errata_1['id'], test_errata_2['id']])

        errata = self.repo_api.errata('some-id', types=['bugfix'])
        self.assertTrue(len(errata) == 2)

        self.repo_api.delete_errata(repo['id'], [test_errata_1['id'], test_errata_2['id']])

        errata = self.repo_api.errata('some-id', types=['bugfix'])
        self.assertTrue(len(errata) == 0)

    def test_consumer_errata(self, repo_id = 'some-id'):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        repo = self.repo_api.create(repo_id, 'some name', \
            'x86_64', 'http://example.com')
        id = 'test_errata_id_1'
        title = 'test_errata_title_1'
        description = 'test_errata_description_1'
        version = '1.0'
        release = '0'
        type = 'bugfix'
        test_errata_1 = self.errata_api.create(id, title, description, version, release, type)
        assert(test_errata_1 is not None)

        epkg = get_rpm_information(my_dir + "/data/pulp-test-package-0.3.1-1.fc11.x86_64.rpm")
        test_pkg_name = epkg["name"]
        test_epoch = epkg["epoch"]
        test_version = epkg["version"]
        test_release = epkg["release"]
        test_arch = epkg["arch"]
        test_description = "test description text"
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = "test-filename-1.2.3-1.el5.x86_64.rpm"
        p = self.package_api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
                release=test_release, arch=test_arch, description=test_description,
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        print "Package! %s" % p
        # Add this package version to the repo
        self.repo_api.add_package(repo["id"], [p['id']])
        test_errata_1["pkglist"] = [{"packages" : [{'src': 'http://download.fedoraproject.org/pub/fedora/linux/updates/11/x86_64/pulp-test-package-0.3.1-1.fc11.x86_64.rpm',
                                                    'name': 'pulp-test-package',
                                                    'filename': 'pulp-test-package-0.3.1-1.fc11.x86_64.rpm',
                                                    'epoch': '0', 'version': '0.3.1', 'release': '1.fc11',
                                                    'arch': 'x86_64'}]}]

        self.errata_api.update(id, Delta(test_errata_1, 'pkglist'))
        self.repo_api.add_errata(repo['id'], (test_errata_1['id'],))

        cid = 'test-consumer'
        c = self.consumer_api.create(cid, 'some consumer desc')
        self.assertTrue(c is not None)

        info1 = get_rpm_information(my_dir + \
                        "/data/pulp-test-package-0.2.1-1.fc11.x86_64.rpm")
        info2 = get_rpm_information(my_dir + \
                        "/data/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm")

        packages = generatePakageProfile([info1, info2])
        c['package_profile'] = packages
        self.assertTrue(c['package_profile'] is not None)
        Consumer.get_collection().save(c, safe=True)

        c["repoids"] = [repo['id']]
        Consumer.get_collection().save(c, safe=True)

        errlist = self.consumer_api.listerrata(c['id'])
        assert(len(errlist) == 1)

        pkguplist = self.consumer_api.list_package_updates(c['id'])['packages']
        assert(len(pkguplist) == 1)

    def test_repo_package_groups(self):
        repo = self.repo_api.create('some-id', 'some name', \
            'i386', 'http://example.com')
        pkggroup = self.repo_api.create_packagegroup(repo["id"],
                'test-group-id', 'test-group-name',
                'test-group-description')
        package = testutil.create_package(self.package_api, 'test_repo_packages')
        self.repo_api.add_package(repo["id"], [package["id"]])
        self.repo_api.add_packages_to_group(repo["id"], pkggroup["id"],
                [package["name"]], gtype="default")
        # Verify package is present in group
        found = self.repo_api.repository('some-id')
        self.assertTrue(found['packagegroups'] is not None)
        self.assertTrue(pkggroup['id'] in found['packagegroups'])
        self.assertTrue(package["name"] in \
                found['packagegroups'][pkggroup['id']]['default_package_names'])
        # Remove package from package group
        self.repo_api.delete_package_from_group(repo["id"], pkggroup["id"],
                package["name"], gtype="default")
        found = self.repo_api.repository('some-id')
        self.assertTrue(found['packagegroups'] is not None)
        self.assertTrue(pkggroup['id'] in found['packagegroups'])
        self.assertTrue(package["name"] not in \
                found['packagegroups'][pkggroup['id']]['default_package_names'])
        # Remove packagegroup from repo
        self.repo_api.delete_packagegroup(repo["id"], pkggroup["id"])
        found = self.repo_api.repository('some-id')
        self.assertTrue(len(found['packagegroups']) == 0)

    def test_repo_package_groups_with_restrict_missing_packages(self):
        repo = self.repo_api.create('test_repo_package_groups_with_restrict_missing_packages',
                                'some name', 'i386', 'http://example.com')
        pkggroup = self.repo_api.create_packagegroup(repo["id"],
                'test-group-id1', 'test-group-name',
                'test-group-description')
        package = testutil.create_package(self.package_api, 'test_repo_package1')
        self.repo_api.add_package(repo["id"], [package["id"]])
        self.repo_api.add_packages_to_group(repo["id"], pkggroup["id"],
                [package["name"]], gtype="default")
        # Add a non-existent package
        missing_pkg_name = "missing_package_name"
        self.repo_api.add_packages_to_group(repo["id"], pkggroup["id"], [missing_pkg_name])
        grps = self.repo_api.packagegroups(id=repo["id"])
        self.assertTrue(grps.has_key(pkggroup["id"]))
        grp = grps[pkggroup["id"]]
        self.assertEquals(2, len(grp["default_package_names"]))
        grps = self.repo_api.packagegroups(id=repo["id"], filter_missing_packages=True)
        self.assertTrue(grps.has_key(pkggroup["id"]))
        grp = grps[pkggroup["id"]]
        self.assertEquals(1, len(grp["default_package_names"]))
        self.assertTrue(missing_pkg_name not in grp["default_package_names"])

    def test_repo_package_groups_with_restrict_incomplete_groups(self):
        repo = self.repo_api.create('test_repo_package_groups_with_restrict_incomplete_groups',
                                'some name', 'i386', 'http://example.com')
        pkggroup1 = self.repo_api.create_packagegroup(repo["id"],
                'test-group-id1', 'test-group-name1',
                'test-group-description1')
        pkggroup2 = self.repo_api.create_packagegroup(repo["id"],
                'test-group-id2', 'test-group-name2',
                'test-group-description2')
        package = testutil.create_package(self.package_api, 'test_repo_package1')
        self.repo_api.add_package(repo["id"], [package["id"]])
        self.repo_api.add_packages_to_group(repo["id"], pkggroup1["id"],
                [package["name"]], gtype="default")
        self.repo_api.add_packages_to_group(repo["id"], pkggroup2["id"],
                [package["name"]], gtype="default")
        # Add a non-existent package
        missing_pkg_name = "missing_package_name"
        self.repo_api.add_packages_to_group(repo["id"], pkggroup2["id"], [missing_pkg_name])
        # Regular package group lookup
        grps = self.repo_api.packagegroups(id=repo["id"])
        self.assertEquals(2, len(grps))
        self.assertTrue(grps.has_key(pkggroup1["id"]))
        self.assertTrue(grps.has_key(pkggroup2["id"]))
        grp = grps[pkggroup2["id"]]
        self.assertEquals(2, len(grp["default_package_names"]))
        # Filtered package group lookup
        grps = self.repo_api.packagegroups(id=repo["id"], filter_incomplete_groups=True)
        self.assertTrue(grps.has_key(pkggroup1["id"]))
        self.assertTrue(not grps.has_key(pkggroup2["id"]))

    def test_repo_package_group_categories(self):
        repo = self.repo_api.create(
            'some-id_pkg_group_categories',
            'some name',
            'i386',
            'http://example.com')
        group = self.repo_api.create_packagegroup(
            repo['id'],
            'test-group-id',
            'test-group-name',
            'test-group-description')
        group.default_package_names.append("test-package-name")
        category = self.repo_api.create_packagegroupcategory(
            repo['id'],
            'test-group-cat-id', 'test-group-cat-name',
            'test-group-cat-description')
        self.repo_api.add_packagegroup_to_category(repo['id'], category['id'], group['id'])
        found = self.repo_api.repository(repo['id'])
        assert(found['packagegroups'] is not None)
        assert(group['id'] in found['packagegroups'])
        assert(found['packagegroupcategories'] is not None)
        assert(category['id'] in found['packagegroupcategories'])

    def __test_consumer_installpackages(self):
        cid = 'bindconsumerid'
        packagenames = ['A', 'B', 'C']
        self.consumer_api.create(cid, 'test install package.')
        result = self.consumer_api.installpackages(cid, packagenames)
        assert(result == packagenames)

    def test_bulk_create(self):
        consumers = []
        my_dir = os.path.abspath(os.path.dirname(__file__))
        info1 = get_rpm_information(my_dir + "/data/pulp-test-package-0.2.1-1.fc11.x86_64.rpm")
        info2 = get_rpm_information(my_dir + "/data/pulp-test-package-0.3.1-1.fc11.x86_64.rpm")
        info3 = get_rpm_information(my_dir + "/data/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm")

        packages = generatePakageProfile([info1, info2, info3])

        for i in range(1005):
            c = Consumer(random_string(), random_string())
            c['package_profile'] = packages
            consumers.append(c)

        self.consumer_api.bulkcreate(consumers)
        all = self.consumer_api.consumers()
        n = len(all)
        assert(n == 1005)

    def test_consumerwithpackage(self, id = 'some-id'):
        c = self.consumer_api.create('test-consumer', 'some consumer desc')
        repo = self.repo_api.create(id, 'some name',
                'i386', 'http://example.com')
        my_dir = os.path.abspath(os.path.dirname(__file__))

        info1 = get_rpm_information(my_dir + "/data/pulp-test-package-0.2.1-1.fc11.x86_64.rpm")
        info2 = get_rpm_information(my_dir + "/data/pulp-test-package-0.3.1-1.fc11.x86_64.rpm")
        info3 = get_rpm_information(my_dir + "/data/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm")

        packages = generatePakageProfile([info1, info2, info3])

        for i in range(10):
            randName = random_string()
            package = testutil.create_package(self.package_api, randName)
            packages.append(package)

        c['package_profile'] = packages
        Consumer.get_collection().save(c, safe=True)
        self.assertTrue(c['package_profile'] is not None)
        ## Look back up from DB
        c = self.consumer_api.consumer(c['id'])
        found = False
        for p in c['package_profile']:
            if (p['name'] == 'pulp-test-package'):
                found = True
        self.assertTrue(found)
        found = self.consumer_api.consumers_with_package_names(['some-invalid-id'])
        assert(len(found) == 0)

        found = self.consumer_api.consumers_with_package_names(['pulp-test-package'])
        assert(len(found) > 0)

        packages = self.consumer_api.packages(c['id'])
        self.assertTrue(packages is not None)
        self.assertTrue(len(packages) > 0)

    def test_json(self):
        repo = self.repo_api.create('some-id', 'some name',
            'i386', 'http://example.com')
        jsonrepo = json.dumps(repo, default=pymongo.json_util.default)
        assert(jsonrepo is not None)
        parsed = json.loads(jsonrepo)
        assert(parsed is not None)
        print parsed

    def cancel_task(self, id = 'some-id'):
        repo = self.repo_api.create(id, 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/')
        self.assertTrue(repo is not None)
        task = repo_sync.sync(repo['id'])
        task.cancel()

    def test_sync_with_wrong_source(self):
        try:
            repo = self.repo_api.create('some-id', 'some name', 'i386',
                                    'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest/')
            self.assertTrue(repo is not None)
        except PulpException:
            pass

    def test_sync_two_repos_same_nevra_different_checksum(self):
        """
        Sync 2 repos that have a package with same NEVRA
        but different checksum
        """
        test_pkg_name = "pulp-test-package-same-nevra"
        my_dir = os.path.abspath(os.path.dirname(__file__))
        repo_name_a = "test_same_nevra_diff_checksum_repo_A"
        repo_name_b = "test_same_nevra_diff_checksum_repo_B"
        datadir_a = my_dir + "/data/sameNEVRA_differentChecksums/A/repo/"
        datadir_b = my_dir + "/data/sameNEVRA_differentChecksums/B/repo/"

        # Create & Sync Repos
        repo_a = self.repo_api.create(repo_name_a, 'some name', 'x86_64',
                                  'file://%s' % datadir_a)
        repo_b = self.repo_api.create(repo_name_b, 'some name', 'x86_64',
                                'file://%s' % datadir_b)
        repo_sync._sync(repo_a["id"])
        repo_sync._sync(repo_b["id"])

        # This will get fixed when we move the async nature of sync down into
        # the API layer

        time.sleep(5)

        # Look up each repo from API
        found_a = self.repo_api.repository(repo_a['id'])
        found_b = self.repo_api.repository(repo_b['id'])

        # Verify each repo has the test package synced
        found_a_pid = None
        for pkg_id in found_a["packages"]:
            p = self.package_api.package(pkg_id)
            if (p['name'].index(test_pkg_name) >= 0):
                found_a_pid = p['id']
        assert(found_a_pid is not None)

        found_b_pid = None
        for pkg_id in found_b["packages"]:
            p = self.package_api.package(pkg_id)
            if (p['name'].index(test_pkg_name) >= 0):
                found_b_pid = p['id']
        assert(found_b_pid is not None)


        packagea = self.package_api.package(found_a_pid)
        packageb = self.package_api.package(found_b_pid)

        # Grab the associated package version (there should only be 1)
        # Ensure that the package versions have different checksums, but all other
        # keys are identical
        for key in ['epoch', 'version', 'release', 'arch', 'filename', 'name']:
            assert (packagea[key] == packageb[key])
        self.assertTrue(packagea['checksum'] != packageb['checksum'])
        #TODO:
        # Add test to compare checksum when it's implemented in Package
        # verify the checksums are different

    def test_sync_two_repos_share_common_package(self):
        """
        Sync 2 repos that share a common package, same NEVRA
        same checksum
        """
        test_pkg_name = "pulp-test-package"
        my_dir = os.path.abspath(os.path.dirname(__file__))
        repo_name_a = "test_two_repos_share_common_pkg_repo_A"
        repo_name_b = "test_two_repos_share_common_pkg_repo_B"
        datadir_a = my_dir + "/data/sameNEVRA_sameChecksums/A/repo/"
        datadir_b = my_dir + "/data/sameNEVRA_sameChecksums/B/repo/"
        # Create & Sync Repos
        repo_a = self.repo_api.create(repo_name_a, 'some name', 'x86_64',
                                'file://%s' % datadir_a)
        repo_b = self.repo_api.create(repo_name_b, 'some name', 'x86_64',
                                'file://%s' % datadir_b)
        repo_sync._sync(repo_a['id'])
        repo_sync._sync(repo_b['id'])
        # Look up each repo from API
        found_a = self.repo_api.repository(repo_a['id'])
        found_b = self.repo_api.repository(repo_b['id'])
        # Verify each repo has the test package synced
        # Verify each repo has the test package synced
        found_a_pid = None
        for pkg_id in found_a["packages"]:
            p = self.package_api.package(pkg_id)
            if (p['name'].index(test_pkg_name) >= 0):
                found_a_pid = p['id']
        assert(found_a_pid is not None)

        found_b_pid = None
        for pkg_id in found_b["packages"]:
            p = self.package_api.package(pkg_id)
            if (p['name'].index(test_pkg_name) >= 0):
                found_b_pid = p['id']
        assert(found_b_pid is not None)
        packagea = self.package_api.package(found_a_pid)
        packageb = self.package_api.package(found_b_pid)

        # Ensure that the 2 Package instances actually point
        # to the same single instance
        assert(repo_a['_id'] != repo_b['_id'])
        assert(packagea['_id'] == packageb['_id'])

    def test_sync(self):
        p = os.path.join(self.data_path, "repo_resync_a")
        repo = self.repo_api.create('some-id', 'some name', 'i386',
                'file://%s' % (p))
        failed = False
        try:
            self.repo_api._sync('invalid-id-not-found')
        except Exception:
            failed = True
        assert(failed)

        repo_sync._sync(repo['id'])

        # Check that local storage has dir and rpms
        d = os.path.join(top_repos_location(), repo['relative_path'])
        self.assertTrue(os.path.isdir(d))
        dirList = os.listdir(d)
        assert(len(dirList) > 0)
        found = self.repo_api.repository(repo['id'])
        packages = found['packages']
        assert(packages is not None)
        assert(len(packages) > 0)

    def resync_removes_deleted_package(self, id = 'test_resync_removes_deleted_package'):
        # Since a repo with 3 packages, simulate the repo source deleted 1 package
        # Re-sync ensure we delete the removed package
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create(id,
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        repo_sync._sync(r["id"])
        # Refresh object now it's been sync'd
        r = self.repo_api.repository(r['id'])
        self.assertTrue(len(r["packages"]) == 3)
        expected_packages = ["pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm",
                "pulp-test-package-0.2.1-1.fc11.x86_64.rpm",
                "pulp-test-package-0.3.1-1.fc11.x86_64.rpm"]
        for ep in expected_packages:
            found = False
            for pkg_id in r["packages"]:
                p = self.package_api.package(pkg_id)
                if p["filename"] == ep:
                    found = True
            self.assertTrue(found)
        # Simulate a change that a package was deleted
        repo_path = os.path.join(self.data_path, "repo_resync_b")
        r = self.repo_api.repository(r["id"])
        d = dict(feed="file://%s" % repo_path)
        self.repo_api.update(r["id"], d)
        repo_sync._sync(r["id"])
        #Refresh Repo Object and Verify Changes
        r = self.repo_api.repository(r["id"])
        self.assertTrue(len(r["packages"]) == 2)
        removed_package = "pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm"
        expected_packages = ["pulp-test-package-0.2.1-1.fc11.x86_64.rpm",
                "pulp-test-package-0.3.1-1.fc11.x86_64.rpm"]
        for ep in expected_packages:
            found = False
            for pkg_id in r["packages"]:
                p = self.package_api.package(pkg_id)
                if p["filename"] == ep:
                    found = True
            self.assertTrue(found)
        for pkg_id in r["packages"]:
            p = self.package_api.package(pkg_id)
            self.assertTrue(p["filename"] != removed_package)

    def disabled_resync_removes_deleted_package_with_two_pkgs_same_nevra(self):
        # Assume we have 2 packages in pulp with same NEVRA
        # 1 of those packages is in a repo
        # the repo is re-synced and that package is not present
        # We need to ensure the package previously associated to the repo
        # is removed and verify the other pkg with same NEVRA info but never
        # part of this repo still exists in pulp
        self.assertTrue(False)

    def test_sync_feedless(self):
        repo = self.repo_api.create('some-id-no-feed', 'some name', 'i386')
        # verify repo without feed is not syncable
        failed = False
        try:
            repo_sync._sync(repo['id'])
        except Exception:
            # raises a PulpException
            # 'This repo is not setup for sync. Please add packages using upload.'
            failed = True
        assert(failed)

    def test_local_sync_callback(self):
        # We need report to be accesible for writing by the callback
        global report
        report = None
        def callback(r):
            global report
            report = r
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/repo_resync_a/"
        repo = self.repo_api.create('some-id', 'some name', 'i386',
                                'file://%s' % datadir)
        repo_sync._sync(repo['id'], progress_callback=callback)
        found = self.repo_api.repository(repo['id'])
        packages = found['packages']
        self.assertTrue(packages is not None)
        self.assertTrue(len(packages) == 3)
        self.assertEqual(report["num_download"], 3)
        self.assertEqual(report["num_error"], 0)
        self.assertEqual(report["num_success"], 3)
        self.assertEqual(report["items_total"], 3)
        self.assertEqual(report["items_left"], 0)
        self.assertEqual(report["size_total"], 6791)
        rpm_details = report["details"]["rpm"]
        self.assertEqual(rpm_details["total_count"], 3)
        self.assertEqual(rpm_details["num_error"], 0)
        self.assertEqual(rpm_details["num_success"], 3)
        self.assertEqual(rpm_details["items_left"], 0)
        self.assertEqual(rpm_details["total_size_bytes"], 6791)
        self.assertEqual(rpm_details["size_left"], 0)

    def test_find_repos_by_package(self):
        # Goal is to search by errata id and discover the repos
        # which contain the errata.
        #
        # Sync 2 repos with same content local feed
        datadir = os.path.join(self.data_path, "sameNEVRA_differentChecksums/A/repo")
        r = self.repo_api.create("test_find_repos_by_package", "test_name", "x86_64",
                "file://%s" % datadir)
        repo_sync._sync(r['id'])
        datadir = os.path.join(self.data_path, "sameNEVRA_differentChecksums/B/repo")
        r2 = self.repo_api.create("test_find_repos_by_package_2", "test_name_2", "x86_64",
                "file://%s" % datadir)
        repo_sync._sync(r2['id'])
        # Refresh object now it's been sync'd
        r = self.repo_api.repository(r['id'])
        r2 = self.repo_api.repository(r2['id'])

        # Test for known pkgid
        self.assertTrue(len(r["packages"]) == 1)
        self.assertTrue(len(r2["packages"]) == 1)
        pkgid1 = r["packages"][0]
        pkgid2 = r2["packages"][0]

        found = self.repo_api.find_repos_by_package(pkgid1)
        self.assertTrue(len(found) == 1)
        self.assertTrue(r["id"] in found)
        found = self.repo_api.find_repos_by_package(pkgid2)
        self.assertTrue(len(found) == 1)
        self.assertTrue(r2["id"] in found)

    def test_repo_package_by_name(self):
        repo = self.repo_api.create('some-id', 'some name', \
            'i386', 'http://example.com')
        p = testutil.create_package(self.package_api, 'test_pkg_by_name', version="1", filename="test01.rpm")
        self.repo_api.add_package(repo["id"], [p['id']])

        p2 = testutil.create_package(self.package_api, 'test_pkg_by_name', version="2", filename="test02.rpm")
        self.repo_api.add_package(repo["id"], [p2['id']])

        pkgs = self.repo_api.get_packages_by_name(repo['id'], p['name'])
        self.assertTrue(len(pkgs) == 2)
        self.assertTrue(p["id"] in pkgs)
        self.assertTrue(p2["id"] in pkgs)

        pkgs = self.repo_api.get_packages_by_name(repo['id'], "bad_name")
        self.assertTrue(len(pkgs) == 0)


    def test_get_packages_by_id(self):
        repo = self.repo_api.create('some-id', 'some name', \
            'i386', 'http://example.com')
        repo2 = self.repo_api.create('some-id-2', 'some name 2', \
            'i386', 'http://example.com-2')
        p1 = testutil.create_package(self.package_api, 'test_pkg_by_name')
        self.repo_api.add_package(repo["id"], [p1['id']])

        p2 = testutil.create_package(self.package_api, 'test_pkg2_by_name')
        self.repo_api.add_package(repo2["id"], [p2['id']])

        pkgs = self.repo_api.get_packages_by_id(repo['id'], [p1['id']])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p1["id"] in pkgs)

        pkgs = self.repo_api.get_packages_by_id(repo2['id'], [p2['id']])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p2["id"] in pkgs)

        pkgs = self.repo_api.get_packages_by_id(repo2['id'], [p1['id']])
        self.assertTrue(len(pkgs) == 0)

    def test_get_packages_by_filename(self):
        repo = self.repo_api.create('some-id', 'some name', \
            'i386', 'http://example.com')
        repo2 = self.repo_api.create('some-id-2', 'some name 2', \
            'i386', 'http://example.com-2')
        p1 = testutil.create_package(self.package_api, 'test_pkg_by_name', filename="test01.rpm")
        self.repo_api.add_package(repo["id"], [p1['id']])

        p2 = testutil.create_package(self.package_api, 'test_pkg2_by_name', filename="test02.rpm")
        self.repo_api.add_package(repo2["id"], [p2['id']])

        pkgs = self.repo_api.get_packages_by_filename(repo['id'], [p1['filename']])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p1["id"] in pkgs)

        pkgs = self.repo_api.get_packages_by_filename(repo2['id'], [p2['filename']])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p2["id"] in pkgs)

        pkgs = self.repo_api.get_packages_by_filename(repo2['id'], [p1['filename']])
        self.assertTrue(len(pkgs) == 0)

        pkgs = self.repo_api.get_packages_by_id(repo2['id'], [])
        self.assertTrue(len(pkgs) == 0)

        pkgs = self.repo_api.get_packages_by_id(repo2['id'], ["bad_name"])
        self.assertTrue(len(pkgs) == 0)

    def test_packages(self):
        repo = self.repo_api.create('some-id', 'some name', \
            'i386', 'http://example.com')
        p1 = testutil.create_package(self.package_api, 'test_pkg_by_name', filename="test01.rpm")
        self.repo_api.add_package(repo["id"], [p1['id']])

        p2 = testutil.create_package(self.package_api, 'test_pkg2_by_name', filename="test02.rpm")
        self.repo_api.add_package(repo["id"], [p2['id']])

        #Create a similar package but dont add to repo
        p3 = testutil.create_package(self.package_api, 'test_pkg_by_name', filename="test03.rpm")

        pkgs = self.repo_api.packages(repo['id'])
        self.assertTrue(len(pkgs) == 2)
        self.assertTrue(p1["id"] in pkgs)
        self.assertTrue(p2["id"] in pkgs)

        pkgs = self.repo_api.packages(repo['id'], name=p1['name'])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p1["id"] in pkgs)

        pkgs = self.repo_api.packages(repo['id'], filename=p2['filename'])
        self.assertTrue(len(pkgs) == 1)
        self.assertTrue(p2["id"] in pkgs)

        pkgs = self.repo_api.packages(repo['id'], version=p1['version'])
        self.assertTrue(len(pkgs) == 2)
        self.assertTrue(p1["id"] in pkgs)
        self.assertTrue(p2["id"] in pkgs)

        pkgs = self.repo_api.packages(repo['id'], name="bad_name")
        self.assertTrue(len(pkgs) == 0)

        # test delete referenced package
        try:
            self.package_api.delete(p1['id'])
            raise Exception, 'package with references, deleted'
        except PackageHasReferences:
            pass

        # test delete orphaned package
        self.package_api.delete(p3['id'])

    def test_add_2_pkg_same_nevra_same_repo(self, id = 'some-same-nevra-id1'):
        repo = self.repo_api.create(id, 'some name', \
            'i386', 'http://example.com')
        p1 = testutil.create_package(self.package_api, 'test_pkg_by_name', filename="test01.rpm", checksum="blah1")
        p2 = testutil.create_package(self.package_api, 'test_pkg_by_name', filename="test01.rpm", checksum="blah2")
        errors, filtered_count = self.repo_api.add_package(repo["id"], [p1['id'],p2['id']])
        self.assertTrue(len(errors), 1)
        # Error format is:  [(id, (n,e,v,r,a), filename, sha256_checksum)]
        self.assertEqual(errors[0][0], p2["id"])
        self.assertEqual(errors[0][1], (p2["name"], p2["epoch"], p2["version"], p2["release"], p2["arch"]))
        self.assertEqual(errors[0][2], p2["filename"])
        self.assertEqual(errors[0][3], p2["checksum"]["sha256"])

    def test_associate_packages(self, id = 'some-associate-pkg-id1'):
        repo1 = self.repo_api.create(id, 'some name', \
            'i386', 'http://example.com')
        repo2 = self.repo_api.create('some-associate-pkg-id2', 'some name', \
            'i386', 'http://example.com')
        p1 = testutil.create_package(self.package_api, 'test_pkg_by_name1', filename="test01.rpm", checksum="blah1")
        p2 = testutil.create_package(self.package_api, 'test_pkg_by_name2', filename="test02.rpm", checksum="blah2")
        p3 = testutil.create_package(self.package_api, 'test_pkg_by_name3', filename="test03a.rpm", checksum="blah3")
        p4 = testutil.create_package(self.package_api, 'test_pkg_by_name3', filename="test03b.rpm", checksum="blah4")
        p5a = testutil.create_package(self.package_api, 'test_pkg_by_name5a', filename="test05.rpm", checksum="blah5a")
        p5b = testutil.create_package(self.package_api, 'test_pkg_by_name5b', filename="test05.rpm", checksum="blah5b")
        # Adding 2 pkg of same NEVRA only 1 should be added (first one).
        # Adding 2 pkg with same filename, only 1 should be added
        # Adding a bogus package, it should not be added since it wasn't created on server
        bad_filename = "bad_filename_doesntexist"
        bad_checksum = "bogus_checksum"
        errors = self.repo_api.associate_packages([((p1["filename"],p1["checksum"]["sha256"]),[repo1["id"],repo2["id"]]), \
            ((p2["filename"],p2["checksum"]["sha256"]),[repo1["id"],repo2["id"]]), \
            ((p3["filename"],p3["checksum"]["sha256"]),[repo1["id"],repo2["id"]]),
            ((p4["filename"],p4["checksum"]["sha256"]),[repo1["id"],repo2["id"]]),
            ((p5a["filename"],p5a["checksum"]["sha256"]),[repo1["id"],repo2["id"]]),
            ((p5b["filename"],p5b["checksum"]["sha256"]),[repo1["id"],repo2["id"]]),
            ((bad_filename,bad_checksum),[repo1["id"],repo2["id"]])])
        found = self.repo_api.repository(repo1['id'])
        self.assertEqual(len(found['packages']), 4)
        self.assertTrue(p1["id"] in found['packages'])
        self.assertTrue(p2["id"] in found['packages'])
        self.assertTrue(p3["id"] in found['packages'])
        self.assertTrue(p4["id"] not in found['packages'])
        self.assertTrue(p5a["id"] in found['packages'])
        self.assertTrue(p5b["id"] not in found['packages'])

        self.assertTrue(bad_filename in errors)
        for e in errors:
            #Error format shoudl be key is the filename
            # value is {'checksum':[repo_id1,repo_id2]}
            self.assertTrue(e in [p4["filename"], p5b["filename"], bad_filename])

    def test_disassociate_packages(self):
        repo1 = self.repo_api.create('some-repopkg-id1', 'some name', \
            'i386', 'http://example.com')
        repo2 = self.repo_api.create('some-repopkg-id2', 'some name', \
            'i386', 'http://example.com')
        p1 = testutil.create_package(self.package_api, 'test_pkg_by_name1', filename="test01.rpm", checksum="blah1")
        p2 = testutil.create_package(self.package_api, 'test_pkg_by_name2', filename="test02.rpm", checksum="blah2")
        p3 = testutil.create_package(self.package_api, 'test_pkg_by_name3', filename="test03.rpm", checksum="blah3")
        # Associate test packages
        errors = self.repo_api.associate_packages(
            [((p1["filename"],p1["checksum"]["sha256"]),[repo1["id"],repo2["id"]]), \
             ((p2["filename"],p2["checksum"]["sha256"]),[repo1["id"],repo2["id"]]), \
             ((p3["filename"],p3["checksum"]["sha256"]),[repo1["id"]]) \
            ])
        found = self.repo_api.repository(repo1['id'])
        self.assertEqual(len(found['packages']), 3)
        self.assertTrue(p1["id"] in found['packages'])
        self.assertTrue(p2["id"] in found['packages'])
        self.assertTrue(p3["id"] in found['packages'])
        # Now do the disassociate portion
        p4 = testutil.create_package(self.package_api, 'test_pkg_by_name4', filename='test04.rpm', checksum='blah4')
        errors = self.repo_api.disassociate_packages(
            [((p1["filename"],p1["checksum"]["sha256"]),[repo1["id"],repo2["id"]]), \
             ((p2["filename"],p2["checksum"]["sha256"]),[repo1["id"],repo2["id"]]), \
             ((p3["filename"],p3["checksum"]["sha256"]),[repo1["id"],repo2["id"]]), \
             ((p4["filename"],p4["checksum"]["sha256"]),[repo1["id"],repo2["id"]]) \
            ])
        # Check for errors
        self.assertEquals(2, len(errors))
        # p3 should reflect it could not be dissociated from repo2 (it didn't belong to repo2)
        self.assertTrue(p3["filename"] in errors.keys())
        self.assertEquals(1, len(errors[p3["filename"]][p3["checksum"]["sha256"]]))
        self.assertTrue(repo2["id"] in errors[p3["filename"]][p3["checksum"]["sha256"]])
        # p4 never belonged to repo1 or repo2 and should reflect an error for both
        self.assertTrue(p4["filename"] in errors.keys())
        self.assertEquals(2, len(errors[p4["filename"]][p4["checksum"]["sha256"]]))
        self.assertTrue(repo1["id"] in errors[p4["filename"]][p4["checksum"]["sha256"]])
        self.assertTrue(repo2["id"] in errors[p4["filename"]][p4["checksum"]["sha256"]])
        # Verify that p1, p2, p3 are no longer part of repo1
        found = self.repo_api.repository(repo1['id'])
        self.assertEqual(len(found['packages']), 0)
        # Verify that p1, p2 are no longer part of repo2
        found = self.repo_api.repository(repo2['id'])
        self.assertEqual(len(found['packages']), 0)

    def test_get_packages_by_nvera(self):
        repo1 = self.repo_api.create('some-nvera-id1', 'some name', \
            'i386', 'http://example.com')
        p1 = testutil.create_package(self.package_api, 'test_pkg_by_name1',
                filename="test01.rpm", checksum="blah1")
        p2 = testutil.create_package(self.package_api, 'test_pkg_by_name2',
                filename="test02.rpm", checksum="blah2")
        p3 = testutil.create_package(self.package_api, 'test_pkg_by_name3',
                filename="test03.rpm", checksum="blah3")
        self.repo_api.add_package(repo1["id"], [p1["id"], p2["id"]])
        nevra = {}
        nevra["name"] = p1["name"]
        nevra["epoch"] = p1["epoch"]
        nevra["version"] = p1["version"]
        nevra["release"] = p1["release"]
        nevra["arch"] = p1["arch"]
        found = self.repo_api.get_packages_by_nvrea(repo1["id"], [nevra], verify_existing=False)
        self.assertTrue(p1["filename"] in found)
        self.assertEquals(found[p1["filename"]]["id"], p1["id"])

        nevra["name"] = p3["name"]
        nevra["epoch"] = p3["epoch"]
        nevra["version"] = p3["version"]
        nevra["release"] = p3["release"]
        nevra["arch"] = p3["arch"]
        found = self.repo_api.get_packages_by_nvrea(repo1["id"], [nevra], verify_existing=False)
        self.assertEquals(len(found), 0)

    def test_duplicate_syncs(self, id = 'some-dup-sync-id'):
        repo = self.repo_api.create(id, 'some name',
            'i386', 'http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/test_bandwidth_repo_smaller/')
        self.assertTrue(self.repo_api.set_sync_in_progress(repo["id"], True))
        caught = False
        try:
            repo_sync._sync(repo["id"])
        except ConflictingOperationException, e:
            caught = True
        self.assertTrue(caught)

    def test_repo_create_with_checksum_type(self, id = 'some-id-no-feed-checksum-type'):
        checksum_type = 'sha1'
        repo = self.repo_api.create(id, 'some name', 'i386', checksum_type=checksum_type)
        repo = self.repo_api.repository(id)
        assert(repo is not None)
        assert(repo['checksum_type'] == checksum_type)
        repodata_file = "%s/%s/%s/%s" % (top_repos_location(),
                                         repo['relative_path'],
                                         'repodata', 'repomd.xml')
        file_type_dump = get_repomd_filetype_dump(repodata_file)
        # validate if checksum types match the specified type
        for ftype, data in file_type_dump.items():
            assert(data['checksum'][0] == checksum_type)

    def test_repo_create_arch(self):
        arches = ['noarch', 'i386', 'i686', 'ppc64', 'ppc',  's390x', 'x86_64', 'ia64']
        for arch in arches:
            repo = self.repo_api.create('repo-id-%s' % arch, 'some name', \
            arch, 'http://example.com')
            assert(repo is not None)
            assert(repo['arch'] is not arch)
            print "created repo %s with arch %s" % (repo['id'], arch)

    def test_empty_repo(self, id = "test_empty_repo_1"):
        repo1 = self.repo_api.create(id, 'some name', 'i386', 'http://example.com', preserve_metadata=True)
        repodata_file1 = "%s/%s/%s/%s" % (top_repos_location(),
                                         repo1['relative_path'],
                                         'repodata', 'repomd.xml')
        # no metadata should exists as its preserved
        self.assertEquals(os.path.exists(repodata_file1), False)
        repo2 = self.repo_api.create("test_empty_repo_2", 'some name', 'i386', 'http://example.com', preserve_metadata=False)
        repodata_file2 = "%s/%s/%s/%s" % (top_repos_location(),
                                         repo2['relative_path'],
                                         'repodata', 'repomd.xml')
        # metadata should exists
        self.assertTrue(os.path.exists(repodata_file2))
        
    def test_add_note(self, id = 'some-add-note-id1'):
        # repo with and without notes added at the creation time 
        repo1 = self.repo_api.create(id, 'some name', 'i386', 'http://example.com')
        repo2 = self.repo_api.create('some-add-note-id2', 'some name', 'i386', 'http://example.com', notes={"key1":"value1"})
        self.repo_api.add_note(repo1['id'], "key2", "value2")
        self.repo_api.add_note(repo2['id'], "key2", "value2")
        repo1 = self.repo_api.repository(repo1['id'])
        repo2 = self.repo_api.repository(repo2['id'])
        assert(repo1["notes"]["key2"] == "value2")
        assert(repo2["notes"]["key2"] == "value2")
        
        # trying to add different value for same key
        try:
            self.repo_api.add_note(repo2['id'], "key2", "value3")
        except PulpException:    
            caught = True
        self.assertTrue(caught)
        
    def test_delete_note(self, id = 'some-del-note-id1'):
        repo1 = self.repo_api.create(id, 'some name', 'i386', 'http://example.com', notes={"key1":"value1","key2":"value2"})
        repo2 = self.repo_api.create('some-del-note-id2', 'some name', 'i386', 'http://example.com', notes={"key1":"value1"})
        self.repo_api.delete_note(repo1['id'], "key1")
        self.repo_api.delete_note(repo2['id'], "key1")
        repo1 = self.repo_api.repository(repo1['id'])
        repo2 = self.repo_api.repository(repo2['id'])
        assert(repo1["notes"] == {"key2":"value2"})
        assert(repo2["notes"] == {})
        
        # try to delete note from repo containing empty notes
        try:
            self.repo_api.delete_note(repo2['id'], "key1")
        except PulpException:
            caught = True
        self.assertTrue(caught)
        
        # try to delete note with non-existing key
        try:
            self.repo_api.delete_note(repo1['id'], "random")
        except PulpException:
            caught = True
        self.assertTrue(caught)
        
    def test_update_repo_notes(self, id = 'some-update-note-id1'):
        repo1 = self.repo_api.create(id, 'some name', 'i386', 'http://example.com', notes={"key1":"value1","key2":"value2"})
        self.repo_api.update_note(repo1['id'], "key1", "value1-changed")
        repo1 = self.repo_api.repository(repo1['id'])
        assert(repo1["notes"]["key1"] == "value1-changed")
        try:
            self.repo_api.update_note(repo1['id'], "random", "random")
        except PulpException:
            caught = True
        self.assertTrue(caught)

    def test_repo_update_checksum_type(self, repo_id = 'test_repo_checksum_type'):
        self.repo_api.create(repo_id, 'Test checksum type', 'noarch')

        #test valid checksum update 
        valid_checksum_type = 'sha'
        self.repo_api.update(repo_id, {'checksum_type' : valid_checksum_type})

        # validate checksum update
        repo_found = self.repo_api.repository(repo_id) 
        assert(valid_checksum_type == repo_found['checksum_type'])

        # validate metadata task was created
        list_of_metadata_info = self.repo_api.list_metadata(repo_found['id'])
        self.assertTrue(list_of_metadata_info is not None)

        #test invalid checksum update 
        failed = False
        try:
            self.repo_api.update(repo_id, {'checksum_type' : 'unknown'})
        except:
            failed = True
        self.assertTrue(failed) 
        
    def test_no_sync_status(self):
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('test_sync_status',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        repo_sync._sync(r["id"])

        sync_status = self.repo_api.get_sync_status(r["id"])
        self.assertEquals(None, sync_status["progress"])
        self.assertEquals(None, sync_status["state"])
        self.assertEquals(None, sync_status["exception"])
        self.assertEquals(None, sync_status["traceback"])
        self.assertEquals(r["id"], sync_status["repoid"])

    def test_running_sync_status(self):
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.repo_api.create('test_sync_status',
                'test_name', 'x86_64', 'file://%s' % (repo_path))
        self.assertTrue(r != None)
        repo_sync._sync(r["id"])

        running_task = Task(repo_sync._sync, [r["id"]])
        running_task.state = task_running
        mock_find_async = mock.Mock(return_value=[running_task])
        self.mock(repo, "find_async", mock_find_async)

        sync_status = self.repo_api.get_sync_status(r["id"])
        self.assertEquals(task_running, sync_status["state"])
        self.assertEquals(r["id"], sync_status["repoid"])

    def test_validate_relative_path(self):
        """
        Tests validating relative paths in the following scenarios:
        - New path is the same as an existing path
        - New path is nested in existing path
        - New path is a parent directory of an existing path
        - New path and existing path are completely different
        - New path contains a subset of an existing path but not at the same root
        - New path and existing path differ only by architecture (common use case)
        - New path and existing path differ only by trailing characters
        - Simple tests with a single directory as the path root
        """

        # Same
        self.assertFalse(repo.validate_relative_path('foo/bar/baz', 'foo/bar/baz'))

        # Nested
        self.assertFalse(repo.validate_relative_path('foo/bar/baz', 'foo/bar'))

        # Parent
        self.assertFalse(repo.validate_relative_path('foo/bar', 'foo/bar/baz'))

        # Distinct
        self.assertTrue(repo.validate_relative_path('foo/bar', 'wombat/zombie'))

        # Subset
        self.assertTrue(repo.validate_relative_path('bar/baz', 'foo/bar/baz/wombat'))

        # Architecture
        self.assertTrue(repo.validate_relative_path('rhel5/i386', 'rhel5/x86_64'))

        # Trailing Characters
        self.assertTrue(repo.validate_relative_path('rhel/repo', 'rhel/repo2'))

        # Single directory tests
        self.assertTrue(repo.validate_relative_path('foo', 'bar'))
        self.assertFalse(repo.validate_relative_path('foo', 'foo/bar'))
        self.assertFalse(repo.validate_relative_path('foo/bar', 'foo'))

    def test_repo_publish_on_create(self):
        repo = self.repo_api.create('repo_publish_true', 'some name',
            'i386', 'http://example.com', publish=True)
        assert(repo is not None)
        self.assertEquals(repo['publish'], True)

        repo = self.repo_api.create('repo_publish_false', 'some name',
            'i386', 'http://example.com', publish=False)
        assert(repo is not None)
        self.assertEquals(repo['publish'], False)

        repo = self.repo_api.create('repo_publish_default', 'some name',
            'i386', 'http://example.com')
        assert(repo is not None)
        self.assertEquals(repo['publish'], True)


