# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import logging
import threading
from datetime import datetime

from pulp.common import dateutils
from pulp.server.compat import ObjectId


_REAPER = None
_LOG = logging.getLogger(__name__)


class CollectionsReaper(object):
    """
    Reaper class that will remove old documents from database collections that
    have been configured for it.

    This class uses the timestamp in the ObjectId that is assigned to the _id
    field of documents to determine which documents to reap from the collection.
    If any documents in a collection have a custom _id field, this reaper will
    not work with that collection.

    @ivar reap_interval: time, in seconds, between checks for old documents
    @type reap_interval: int or float
    @ivar collections: dictionary of collections and the time delta which constitutes an old document
    @type collections: dict
    """

    def __init__(self, reap_interval):
        self.reap_interval = reap_interval
        self.collections = {}

        self.__exit = False
        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)
        self.__reaper = None

    # reap management ------------------------------------------------------

    def __reap(self):
        self.__lock.acquire()

        while True:
            self.__condition.wait(timeout=self.reap_interval)
            if self.__exit:
                if self.__lock is not None:
                    self.__lock.release()
                return
            try:
                self._reap_expired_collection_entries()
            except Exception, e:
                _LOG.critical('Unhandled exception in collections reaper reap: %s' % repr(e))
                _LOG.exception(e)

    def _reap_expired_collection_entries(self):
        for collection, delta in self.collections:
            expired_object_id = self._create_expired_object_id(delta)
            self._remove_expired_entries(collection, expired_object_id)

    def _create_expired_object_id(self, delta):
        now = datetime.now(dateutils.utc_tz())
        expired_datetime = now - delta
        expired_object_id = ObjectId.from_datetime(expired_datetime)
        return expired_object_id

    def _remove_expired_entries(self, collection, expired_object_id):
        collection.remove({'_id': {'$lte': expired_object_id}}, safe=True)

    def start(self):
        """
        Start the reaper thread.
        """
        assert self.__reaper is None
        self.__lock.acquire()
        self.__exit = False # needed for re-starts
        try:
            self.__reaper = threading.Thread(target=self.__reap)
            self.__reaper.setDaemon(True)
            self.__reaper.start()
        finally:
            self.__lock.release()

    def stop(self):
        """
        Stop the reaper thread and wait for it to exit.
        """
        assert self.__reaper is not None
        self.__lock.acquire()
        self.__exit = True
        self.__condition.notify()
        self.__lock.release()
        self.__reaper.join()
        self.__reaper = None

    # collection management ----------------------------------------------------

    def add_collection(self, collection, **delta_kwargs):
        """
        Add a collection to be reaped on the specified intervals.
        Valid intervals and values for delta_kwargs are:
         * years
         * months
         * weeks
         * days
         * hours
         * minutes
         * seconds
        @param collection: database collection to reap documents from
        @type collection: pymongo.collection.Collection
        @param delta_kwargs: key word arguments for time intervals
        """
        self.__lock.acquire()
        try:
            expiration_delta = dateutils.delta_from_key_value_pairs(delta_kwargs)
            self.collections[collection] = expiration_delta
        finally:
            self.__lock.release()

    def remove_collection(self, collection):
        """
        Remove a database collection from the reaper.
        @param collection: database collection to no longer be reaped
        @type collection: pymongo.collection.Collection
        """
        self.__lock.acquire()
        try:
            self.collections.pop(collection, None)
        finally:
            self.__lock.release()

# public api -------------------------------------------------------------------

def initialize():
    """
    Instantiate the global reaper, start it, and add the appropriate collections
    to be reaped from it.
    """
    global _REAPER
    assert _REAPER is None
    _REAPER = CollectionsReaper(1) # need configurable reap interval
    _REAPER.start()

    # NOTE add collections to reap here:


def finalize():
    """
    Delete the global reaper and wait for it's thread to exit.
    NOTE: not used by the server but useful for testing.
    """
    global _REAPER
    assert _REAPER is not None
    _REAPER.stop()
    _REAPER = None
