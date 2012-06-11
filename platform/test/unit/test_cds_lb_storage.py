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

import fcntl
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.cds.lb import storage


TEST_STORAGE_FILE = '/tmp/cds-lb-storage-test'
TEST_LOCK_FILE = '/tmp/cds-lb-storage-lock'


class FilePermutationStoreTest(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)

        if os.path.exists(TEST_STORAGE_FILE):
            os.remove(TEST_STORAGE_FILE)

        if os.path.exists(TEST_LOCK_FILE):
            os.remove(TEST_LOCK_FILE)

    def test_no_file(self):
        """
        Tests that using a file store without the file first existing works correctly.
        This test also verifies that the file lock is released correctly by attempting
        to acquire it again after close() is called.
        """

        # Setup
        if os.path.exists(TEST_STORAGE_FILE):
            os.remove(TEST_STORAGE_FILE)

        self.assertTrue(not os.path.exists(TEST_STORAGE_FILE))

        # Test
        file_store = storage.FilePermutationStore(TEST_STORAGE_FILE, TEST_LOCK_FILE)

        file_store.open()
        file_store.permutation = ['a', 'b', 'c']
        file_store.save()
        file_store.close()

        # Verify
        lock_file = open(TEST_LOCK_FILE, 'w')
        fcntl.flock(lock_file, fcntl.LOCK_EX)

        fp_read = open(TEST_STORAGE_FILE, 'r')
        contents = fp_read.read()
        fp_read.close()

        self.assertEqual(file_store.permutation, contents.split('\n'))

        lock_file.close()

    def test_reread_storage_file(self):
        """
        Tests multiple reads/writes to the storage to make sure they are saved
        correctly.
        """

        # Test
        file_store = storage.FilePermutationStore(TEST_STORAGE_FILE, TEST_LOCK_FILE)

        file_store.open()
        file_store.permutation = ['a', 'b']
        file_store.save()
        file_store.close()

        file_store = storage.FilePermutationStore(TEST_STORAGE_FILE, TEST_LOCK_FILE)

        file_store.open()
        self.assertEqual(['a', 'b'], file_store.permutation)

        file_store.permutation = ['a', 'b', 'c']
        file_store.save()
        file_store.close()

        # Verify

        #   Verify in a loaded FilePermutationStore
        file_store = storage.FilePermutationStore(TEST_STORAGE_FILE, TEST_LOCK_FILE)
        file_store.open()

        self.assertEqual(3, len(file_store.permutation))
        self.assertEqual(['a', 'b', 'c'], file_store.permutation)

        file_store.close()

        #   Verify the file directly
        fp_read = open(TEST_STORAGE_FILE, 'r')
        contents = fp_read.read()
        fp_read.close()

        self.assertEqual(['a', 'b', 'c'], contents.split('\n'))
