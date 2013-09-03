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

from datetime import timedelta
from threading import Thread
from types import NoneType

from isodate import Duration

import base

from pulp.server.compat import ObjectId
from pulp.server.db import reaper
from pulp.server.db.model.consumer import ConsumerHistoryEvent


class ReaperInstantiationTests(base.PulpServerTests):

    def test_instantiation(self):
        try:
            reaper.CollectionsReaper(1)
        except Exception, e:
            self.fail(str(e))

    def test_initialize_finalize(self):
        self.assertTrue(isinstance(reaper._REAPER, NoneType))
        reaper.initialize()
        self.assertTrue(isinstance(reaper._REAPER, reaper.CollectionsReaper))
        reaper.finalize()
        self.assertTrue(isinstance(reaper._REAPER, NoneType))


class BaseReaperTests(base.PulpServerTests):

    def setUp(self):
        super(BaseReaperTests, self).setUp()
        self.reaper = reaper.CollectionsReaper(1)

    def tearDown(self):
        super(BaseReaperTests, self).tearDown()
        self.reaper = None


class ReaperControlTests(BaseReaperTests):

    def test_start_stop(self):
        self.reaper.start()
        self.assertTrue(isinstance(self.reaper._CollectionsReaper__reaper, Thread))
        self.assertFalse(self.reaper._CollectionsReaper__exit)
        self.reaper.stop()
        self.assertTrue(isinstance(self.reaper._CollectionsReaper__reaper, NoneType))
        self.assertTrue(self.reaper._CollectionsReaper__exit)

    def test_add_remove(self):
        collection = ConsumerHistoryEvent.get_collection()
        self.reaper.add_collection(collection, days=1)
        self.assertTrue(collection in self.reaper.collections)
        self.assertTrue(isinstance(self.reaper.collections[collection], timedelta))
        self.reaper.remove_collection(collection)
        self.assertFalse(collection in self.reaper.collections)

    def test_add_remove_duration(self):
        collection = ConsumerHistoryEvent.get_collection()
        self.reaper.add_collection(collection, months=1)
        self.assertTrue(collection in self.reaper.collections)
        self.assertTrue(isinstance(self.reaper.collections[collection], Duration))
        self.reaper.remove_collection(collection)
        self.assertFalse(collection in self.reaper.collections)


class ReaperReapingTests(BaseReaperTests):

    def setUp(self):
        super(ReaperReapingTests, self).setUp()
        self.collection = ConsumerHistoryEvent.get_collection()

    def tearDown(self):
        super(ReaperReapingTests, self).tearDown()
        self.collection.remove({}, safe=True)
        self.collection = None

    def test_expired_object_id(self):
        expired_oid = self.reaper._create_expired_object_id(timedelta(seconds=1))
        self.assertTrue(isinstance(expired_oid, ObjectId))
        now_oid = ObjectId()
        self.assertTrue(now_oid > expired_oid)

    def test_remove_expired_entries(self):
        event = ConsumerHistoryEvent('consumer', 'originator', 'consumer_registered', {})
        self.collection.insert(event, safe=True)
        self.assertTrue(self.collection.find({'_id': event['_id']}).count() == 1)
        expired_oid = self.reaper._create_expired_object_id(timedelta(seconds=-1))
        self.reaper._remove_expired_entries(self.collection, expired_oid)
        self.assertTrue(self.collection.find({'_id': event['_id']}).count() == 0)


