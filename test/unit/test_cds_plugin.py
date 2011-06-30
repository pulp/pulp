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

import os
import sys
import shutil

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import mocks
from pulp.cds.cdslib import loginit, CdsLib, SecretFile
from pulp.cds.lb import storage

# test root dir
ROOTDIR = '/tmp/pulp-cds'

TEST_STORAGE_FILE = '/tmp/cds-plugin-storage-test'
TEST_LOCK_FILE = '/tmp/cds-plugin-storage-lock'

# setup logging
loginit(os.path.join(ROOTDIR, 'cds.log'))

class TestCdsPlugin(testutil.PulpAsyncTest):

    def clean(self):
        testutil.PulpAsyncTest.clean(self)

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)

        if not self.config.has_section('cds'):
            self.config.add_section('cds')
        self.config.set('cds', 'packages_dir', os.path.join(ROOTDIR, 'packages'))
        self.config.set('cds', 'sync_threads', '3')
        self.cds = CdsLib(self.config)

        if os.path.exists(TEST_STORAGE_FILE):
            os.remove(TEST_STORAGE_FILE)

        if os.path.exists(TEST_LOCK_FILE):
            os.remove(TEST_LOCK_FILE)

        self.storage_default_file = storage.DEFAULT_FILE_STORE
        self.storage_default_lock = storage.DEFAULT_FILE_LOCK

        storage.DEFAULT_FILE_STORE = TEST_STORAGE_FILE
        storage.DEFAULT_FILE_LOCK = TEST_LOCK_FILE
        
    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)
        shutil.rmtree(ROOTDIR, True)
        storage.DEFAULT_FILE_STORE = self.storage_default_file
        storage.DEFAULT_FILE_LOCK = self.storage_default_lock

    def test_initialize(self):
        self.cds.initialize()

    def test_release(self):
        self.cds.release()

    def test_secret(self):
        uuid = 'mysecret'
        path = os.path.join(ROOTDIR, 'gofer/.secret')
        secret = SecretFile(path)
        secret.write(uuid)
        f = open(path)
        s = f.read()
        f.close()
        self.assertEqual(uuid, s)
        s = secret.read()
        self.assertEqual(uuid, s)
        secret.delete()
        self.assertFalse(os.path.exists(path))
