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
from logging import basicConfig

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.api.keystore import KeyStore
from pulp.server.util import top_gpg_location as lnkdir
from pulp.server.util import top_repos_location as keydir

KEYS = (
    ('key1', '----BEGIN PGP PUBLIC KEY BLOCK-----\ncontent1'),
    ('key2', '----BEGIN PGP PUBLIC KEY BLOCK-----\ncontent2'),
    ('key3', '----BEGIN PGP PUBLIC KEY BLOCK-----\ncontent3'),
)

REPO = 'fedora'
KEYDIR = os.path.join(keydir(), REPO)
PUBDIR = os.path.join(lnkdir(), REPO)

basicConfig()
testutil.load_test_config()

class TestKeyStore(testutil.PulpAsyncTest):

    def clean(self):
        testutil.PulpAsyncTest.clean(self)
        shutil.rmtree(keydir(), True)
        shutil.rmtree(lnkdir(), True)

    def verify(self):
        # validate files & links
        for root in (KEYDIR, PUBDIR):
            files = os.listdir(root)
            files.sort()
            self.assertEqual(len(files), len(KEYS))
            i = 0
            for fn in files:
                self.assertEqual(fn, KEYS[i][0])
                path = os.path.join(root, fn)
                f = open(path)
                content = f.read()
                f.close()
                self.assertEqual(content, KEYS[i][1])
                i += 1

    def test_add(self):
        self.clean()
        ks = KeyStore(REPO)
        ks.add(KEYS)
        self.verify()

    def test_list(self):
        self.clean()
        ks = KeyStore(REPO)
        ks.add(KEYS)
        i = 0
        for path in sorted(ks.list()):
            self.assertEqual(os.path.dirname(path), REPO)
            self.assertEqual(os.path.basename(path), KEYS[i][0])
            path = os.path.join(keydir(), path)
            f = open(path)
            content = f.read()
            f.close()
            self.assertEqual(content, KEYS[i][1])
            i += 1

    def test_key_and_content(self):
        self.clean()
        ks = KeyStore(REPO)
        ks.add(KEYS)
        keylist = ks.keys_and_contents()
        for key in KEYS:
            name = key[0]
            content = key[1]
            self.assertEqual(content, keylist[name])

    def test_delete(self):
        self.clean()
        ks = KeyStore(REPO)
        ks.add(KEYS)
        self.verify()
        ks.delete([k[0] for k in KEYS])
        self.assertEqual(len(os.listdir(KEYDIR)), 0)
        self.assertEqual(len(os.listdir(PUBDIR)), 0)

    def test_relink(self):
        self.clean()
        ks = KeyStore(REPO)
        ks.add(KEYS)
        self.verify()
        ks.relink()
        self.verify()
