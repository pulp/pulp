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
"""
This module contains tests for the pulp.server.db.reaper module.
"""
from datetime import timedelta
import unittest

import mock

from ... import base
from pulp.server.compat import ObjectId
from pulp.server.db import reaper
from pulp.server.db.model import celery_result, consumer, dispatch, repo_group, repository
from pulp.server.db.model.consumer import ConsumerHistoryEvent
from pulp.server.db.model.reaper_base import _create_expired_object_id, ReaperMixin


class TestReaperCollectionConfig(unittest.TestCase):
    """
    Test for expected items in the reaper configuration.
    """
    def test_reaper_collections(self):
        """
        Test that the expected key-value pairs exist in the reaper collection to timedelta mapping.
        """
        collections_to_reap = [dispatch.ArchivedCall,
                               dispatch.TaskStatus,
                               consumer.ConsumerHistoryEvent,
                               repository.RepoSyncResult,
                               repository.RepoPublishResult,
                               repo_group.RepoGroupPublishResult,
                               celery_result.CeleryResult]
        for key in collections_to_reap:
            self.assertTrue(key in reaper._COLLECTION_TIMEDELTAS)
        # Also check the values.
        self.assertEqual(reaper._COLLECTION_TIMEDELTAS[dispatch.ArchivedCall], 'archived_calls')
        self.assertEqual(reaper._COLLECTION_TIMEDELTAS[dispatch.TaskStatus], 'task_status_history')
        self.assertEqual(reaper._COLLECTION_TIMEDELTAS[consumer.ConsumerHistoryEvent], 'consumer_history')
        self.assertEqual(reaper._COLLECTION_TIMEDELTAS[repository.RepoSyncResult], 'repo_sync_history')
        self.assertEqual(reaper._COLLECTION_TIMEDELTAS[repository.RepoPublishResult],
                         'repo_publish_history')
        self.assertEqual(reaper._COLLECTION_TIMEDELTAS[repo_group.RepoGroupPublishResult],
                         'repo_group_publish_history')
        self.assertEqual(reaper._COLLECTION_TIMEDELTAS[celery_result.CeleryResult],
                         'task_result_history')

class TestCreateExpiredObjectId(unittest.TestCase):
    """
    Assert correct behavior from _create_expired_object_id().
    """

    def test_expired_object_id(self):
        """
        Make sure that _create_expired_object_id() generates correct ObjectIds.
        """
        expired_oid = _create_expired_object_id(timedelta(seconds=1))

        # The oid should be about a second, but since we didn't create the now_oid until after we
        # ran the _create_expired_object_id() function, we can't assert that the timedelta is
        # exactly one second. It should definitely be less than two seconds of difference between
        # them, however (unless Nose is really struggling to run the tests), so we can make sure
        # it fits inside the window of 1 - 2 seconds.
        now_oid = ObjectId()
        self.assertTrue(
            (now_oid.generation_time - expired_oid.generation_time) >= timedelta(seconds=1))
        self.assertTrue(
            (now_oid.generation_time - expired_oid.generation_time) < timedelta(seconds=2))
        # Also, let's make sure the type is correct
        self.assertTrue(isinstance(expired_oid, ObjectId))


class TestReapInheritance(unittest.TestCase):
    """
    Check class inheritance related to ReaperMixin

    Assert that any class used as a key in reaper._COLLECTION_TIMEDELTAS properly inherits from
    reaper_base.ReaperMixin
    """

    def test_assert_inheritance(self):
        """
        The reaper relies on a classmethod to do the document deletion of old documents in a given
        collection. Any model type that needs to be reaped should inherit that classmethod from
        the reaper_base.ReaperMixin class. The reaper runs on any document used as a key in
        reaper._COLLECTION_TIMEDELTAS, so each of those should be asserted as inheriting from
        ReaperMixin.
        """
        for model in reaper._COLLECTION_TIMEDELTAS.keys():
            self.assertTrue(issubclass(model, ReaperMixin))


class TestReapExpiredDocuments(base.PulpServerTests):
    """
    This test class asserts correct behavior from the reap_expired_documents() Task.
    """
    def tearDown(self):
        """
        Clean up the records we made.
        """
        super(TestReapExpiredDocuments, self).tearDown()
        ConsumerHistoryEvent.get_collection().remove()

    @mock.patch('pulp.server.db.reaper.pulp_config.config.getfloat')
    def test_leave_unexpired_entries(self, getfloat):
        chec = ConsumerHistoryEvent.get_collection()
        event = ConsumerHistoryEvent('consumer', 'originator', 'consumer_registered', {})
        chec.insert(event, safe=True)
        self.assertTrue(chec.find({'_id': event['_id']}).count() == 1)
        # Let's mock getfloat to pretend that the user said they want to reap things that are a day
        # old. This means that the event should not get reaped.
        getfloat.return_value = 1.0

        reaper.reap_expired_documents()

        # The event should still exist
        self.assertTrue(chec.find({'_id': event['_id']}).count() == 1)

    @mock.patch('pulp.server.db.reaper.pulp_config.config.getfloat')
    def test_remove_expired_entries(self, getfloat):
        chec = ConsumerHistoryEvent.get_collection()
        event = ConsumerHistoryEvent('consumer', 'originator', 'consumer_registered', {})
        chec.insert(event, safe=True)
        self.assertTrue(chec.find({'_id': event['_id']}).count() == 1)
        # Let's mock getfloat to pretend that the user said they want to reap things from the
        # future, which should make the event we just created look old enough to delete
        getfloat.return_value = -1.0

        reaper.reap_expired_documents()

        # The event should no longer exist
        self.assertTrue(chec.find({'_id': event['_id']}).count() == 0)
