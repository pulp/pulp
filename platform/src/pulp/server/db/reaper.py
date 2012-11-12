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

    def __init__(self, dispatch_interval):
        self.dispatch_interval = dispatch_interval
        self.collections = {}

        self.__exit = False
        self.__lock = threading.RLock()
        self.__condition = threading.Condition(self.__lock)
        self.__dispatcher = None

    # dispatch management ------------------------------------------------------

    def __dispatch(self):
        self.__lock.acquire()

        while True:
            self.__condition.wait(timeout=self.dispatch_interval)
            if self.__exit:
                if self.__lock is not None:
                    self.__lock.release()
                return
            try:
                self._reap_expired_collection_entries()
            except Exception, e:
                _LOG.critical('Unhandled exception in collections reaper dispatch: %s' % repr(e))
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
        assert self.__dispatcher is None
        self.__lock.acquire()
        self.__exit = False # needed for re-starts
        try:
            self.__dispatcher = threading.Thread(target=self.__dispatch)
            self.__dispatcher.setDaemon(True)
            self.__dispatcher.start()
        finally:
            self.__lock.release()

    def stop(self):
        assert self.__dispatcher is not None
        self.__lock.acquire()
        self.__exit = True
        self.__condition.notify()
        self.__lock.release()
        self.__dispatcher.join()
        self.__dispatcher = None

    # collection management ----------------------------------------------------

    def add_collection(self, collection, **delta_kwargs):
        self.__lock.acquire()
        try:
            expiration_delta = dateutils.delta_from_key_value_pairs(delta_kwargs)
            self.collections[collection] = expiration_delta
        finally:
            self.__lock.release()

    def remove_collection(self, collection):
        self.__lock.acquire()
        try:
            self.collections.pop(collection, None)
        finally:
            self.__lock.release()

# public api -------------------------------------------------------------------

def initialize():
    global _REAPER
    assert _REAPER is None
    _REAPER = CollectionsReaper(1) # need configurable dispatch interval
    _REAPER.start()

    # NOTE add collections to reap here:


def finalize():
    global _REAPER
    assert _REAPER is not None
    _REAPER.stop()
    _REAPER = None
