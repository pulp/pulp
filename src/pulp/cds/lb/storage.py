#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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

"""
Contains storage mechanisms for CDS hostname permutations used by the CDS
load balancer.
"""

import fcntl
import logging
import os
from threading import RLock

# -- constants ----------------------------------------------------------------

LOG = logging.getLogger(__name__)

DEFAULT_FILE_LOCK = '/var/lib/pulp-cds/.group-members-lock'
DEFAULT_FILE_STORE = '/var/lib/pulp-cds/.group-members'

# -- storage implementations ---------------------------------------------------

class FilePermutationStore:
    """
    Uses a file as the storage for CDS hostname permutations. Access to the
    underlying file is locked, protecting access to it between the load balancer
    WSGI process and the CDS gofer plugin.
    """

    def __init__(self, store_filename=DEFAULT_FILE_STORE, lock_filename=DEFAULT_FILE_LOCK):
        """
        Creates a new hook to access a file store. No loading of the contents of the
        underlying file is performed.

        @param store_filename: full path to the underlying file backing the storage
        @type  store_filename: str

        @param lock_filename: full path to the file used to prevent concurrent access
        @type  lock_filename: str
        """
        self.store_filename = store_filename
        self.lock_filename = lock_filename

        self.lock_file = None
        self._thread_lock = RLock()
        
        self.permutation = []

    def open(self):
        """
        Opens the underlying file for reading/writing. This will lock the file,
        so it is important to call close() when finished. This call is thread-safe
        in that it will only allow one thread in the same process to open the
        file (yes, that had to be explicitly added for some unholy reason).
        """

        # Acquire the thread lock
        self._thread_lock.acquire()

        # Acquire the file lock
        self.lock_file = open(self.lock_filename, 'w')
        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX)

        # Read in the permutation if it exists
        if os.path.exists(self.store_filename):
            fp_read = open(self.store_filename, 'r')
            permutation_string = fp_read.read()
            fp_read.close()

            self.permutation = [p for p in permutation_string.split('\n') if p != '']
        else:
            self.permutation = []

    def close(self):
        """
        Saves the current state of permutations and releases all locks.
        """

        # Save the permutation
        fp_write = open(self.store_filename, 'w')
        fp_write.write('\n'.join(self.permutation))
        fp_write.close()

        # Release the file lock
        try:
            self.lock_file.close()
            self.lock_file = None
        except:
            LOG.exception('Error releasing file lock for file [%s]' % self.lock_filename)

        # Release the thread lock
        self._thread_lock.release()
