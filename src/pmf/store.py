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
from pmf.window import Window
from time import sleep
from stat import *
from threading import Thread, RLock
from logging import getLogger

log = getLogger(__name__)


class PendingQueue:
    """
    Persistent (local) storage of I{pending} envelopes that have
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

    ROOT = '/tmp/pmf' # TODO: Change to /var/lib/pmf

    def __init__(self, id):
        """
        @param id: The queue id.
        @type id: str
        """
        self.id = id
        self.pending = []
        self.uncommitted = []
        self.__lock = RLock()
        self.mkdir()
        self.load()

    def add(self, envelope):
        """
        Enqueue the specified envelope.
        @param envelope: An L{Envelope}
        @type envelope: L{Envelope}
        """

        fn = self.fn(envelope)
        f = open(fn, 'w')
        f.write(envelope.dump())
        f.close()
        log.info('{%s} add pending:\n%s', self.id, envelope)
        self.lock()
        try:
            self.pending.insert(0, envelope)
        finally:
            self.unlock()

    def next(self, wait=1):
        """
        Get the next pending envelope.
        @param wait: The number of seconds to wait for a pending item.
        @type wait: int
        @return envelope: An L{Envelope}
        @rtype: L{Envelope}
        """
        self.lock()
        try:
            queue = self.pending[:]
        finally:
            self.unlock()
        while wait:
            if queue:
                envelope = queue.pop()
                window = Window(envelope.window)
                if window.future():
                    log.info('{%s} deferring:\n%s', self.id, envelope)
                    continue
                self.remove(envelope)
                log.info('{%s} next:\n%s', self.id, envelope)
                return envelope
            else:
                sleep(1)
                wait -= 1

    def remove(self, envelope):
        """
        Remove the specified envelope and place on the uncommitted list.
        @return envelope: An L{Envelope}
        @rtype: L{Envelope}
        """
        self.lock()
        try:
            self.pending.remove(envelope)
            self.uncommitted.append(envelope)
        finally:
            self.unlock()

    def commit(self):
        """
        Commit envelopes removed from the queue.
        @return: self
        @rtype: L{PendingQueue}
        """
        self.lock()
        try:
            uncommitted = self.uncommitted[:]
        finally:
            self.unlock()
        for envelope in uncommitted:
            fn = self.fn(envelope)
            log.info('{%s} commit:%s', self.id, envelope.sn)
            try:
                os.remove(fn)
            except Exception, e:
                log.exception(e)
        self.lock()
        try:
            self.uncommitted = []
        finally:
            self.unlock()
        return self

    def load(self):
        """
        Load the in-memory queue from filesystem.
        """

        path = os.path.join(self.ROOT, self.id)
        pending = []
        for fn in os.listdir(path):
            path = os.path.join(self.ROOT, self.id, fn)
            envelope = Envelope()
            f = open(path)
            s = f.read()
            f.close()
            envelope.load(s)
            ctime = self.created(path)
            pending.append((ctime, envelope))
        pending.sort()
        self.lock()
        try:
            self.pending = [p[1] for p in pending]
        finally:
            self.unlock()

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

    def fn(self, envelope):
        """
        Get the qualified file name for the envelope.
        @return envelope: An L{Envelope}
        @rtype: L{Envelope}
        @return: The absolute file path.
        @rtype: str
        """
        return os.path.join(self.ROOT, self.id, envelope.sn)
    
    def lock(self):
        self.__lock.acquire()
        
    def unlock(self):
        self.__lock.release()


class PendingReceiver(Thread):
    """
    A pending queue receiver.
    @ivar __run: The main run loop flag.
    @type __run: bool
    @ivar queue: The L{PendingQueue} being read.
    @type queue: L{PendingQueue)
    @ivar consumer: The queue listener.
    @type consumer: L{pmf.consumer.Consumer}
    """

    def __init__(self, queue, listener):
        self.__run = True
        self.queue = queue
        self.listener = listener
        Thread.__init__(self, name='pending:%s' % queue.id)

    def run(self):
        """
        Main receiver (thread).
        Read and dispatch envelopes.
        """
        log.info('{%s} started', self.name)
        while self.__run:
            envelope = self.queue.next(3)
            if envelope:
                self.dispatch(envelope)
                self.queue.commit()

    def dispatch(self, envelope):
        """
        Dispatch the envelope to the listener.
        @return envelope: An L{Envelope} to be dispatched.
        @rtype: L{Envelope}
        """
        try:
            self.listener.dispatch(envelope)
        except Exception, e:
            log.exception(e)

    def stop(self):
        """
        Stop the receiver.
        """
        self.__run = False
        log.info('{%s} stopping', self.name)
