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
#

"""
Provides (local) message storage classes.
"""

import os
from pmf import *
from time import sleep
from stat import *

class PendingQueue:
    """
    File based storage of I{pending} envelopes that have
    been processed of an AMQP queue.  Most likely use is for messages
    with a future I{window} which cannot be processed immediately.
    @cvar ROOT: The root directory used for storage.
    @type ROOT: str
    @ivar id: The queue id.
    @type id: str
    @ivar lastmod: Last (directory) modification.
    @type lastmod: int
    @ivar pending: The queue of pending envelopes.
    @type pending: [Envelope,..]
    @ivar uncommitted: A list (removed) of files pending commit.
    @type uncommitted: [path,..]
    """

    ROOT = '/tmp/pmf'

    def __init__(self, id):
        """
        @param id: The queue id.
        @type id: str
        """
        self.id = id
        self.lastmod = 0
        self.pending = []
        self.uncommitted = []
        self.mkdir()

    def enqueue(self, envelope):
        """
        Enqueue the specified envelope.
        @param envelope: An L{Envelope}
        @type envelope: L{Envelope}
        """
        path = os.path.join(self.ROOT, self.id, envelope.sn)
        f = open(path, 'w')
        f.write(envelope.dump())
        f.close()
        self.load()

    def next(self, block=True):
        """
        Get the next pending envelope.
        @param block: Indicates if call should block when empty.
        @type block: bool
        @return envelope: An L{Envelope}
        @rtype: L{Envelope}
        """
        while block:
            self.load()
            if self.pending:
                p = self.pending[-1]
                f = open(p[1])
                s = f.read()
                f.close()
                envelope = Envelope()
                envelope.load(s)
                self.pending.remove(p)
                self.uncommitted.append(p[1])
                return envelope
            else:
                sleep(1)

    def commit(self):
        """
        Commit items removed from the queue.
        """
        for path in self.uncommitted():
            os.remove(path)
        return self

    def load(self):
        """
        Load the in-memory queue from filesystem.
        Only when directory has been modified since last load.
        """
        path = os.path.join(self.ROOT, self.id)
        mtime = self.modified(path)
        if mtime == self.lastmod:
            return
        self.pending = []
        self.uncommitted = []
        self.lastmod = mtime
        for fn in os.listdir(path):
            path = os.path.join(self.ROOT, self.id, fn)
            ctime = self.created(path)
            self.pending.append((ctime, path))
        self.pending.sort()

    def created(self, path):
        """
        Get create timestamp.
        @return: The file create timestamp.
        @rtype: int
        """
        stat = os.stat(path)
        return stat[ST_CTIME]

    def modified(self, path):
        """
        Get modification timestamp.
        @return: The file modification timestamp.
        @rtype: int
        """
        stat = os.stat(path)
        return stat[ST_MTIME]

    def mkdir(self):
        """
        Ensure the directory exists.
        """
        path = os.path.join(self.ROOT, self.id)
        if not os.path.exists(path):
            os.makedirs(path)