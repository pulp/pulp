# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import time
import unittest

from bson import ObjectId
import mock

from pulp.server import exceptions
from pulp.server.db.connection import initialize
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.managers.schedule import utils


initialize()


class TestGet(unittest.TestCase):
    schedule_id1 = str(ObjectId())
    schedule_id2 = str(ObjectId())

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_query(self, mock_query):
        mock_query.return_value = SCHEDULES

        ret = list(utils.get([self.schedule_id1, self.schedule_id2]))

        self.assertEqual(mock_query.call_count, 1)
        # there should only be 1 argument, a criteria
        self.assertEqual(len(mock_query.call_args[0]), 1)
        criteria = mock_query.call_args[0][0]
        self.assertTrue(isinstance(criteria, Criteria))
        self.assertEqual(criteria.filters, {'_id': {'$in': [ObjectId(self.schedule_id1), ObjectId(self.schedule_id2)]}})

        # three instances of ScheduledCall should be returned
        self.assertEqual(len(ret), 3)
        for schedule in ret:
            self.assertTrue(isinstance(schedule, ScheduledCall))

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_empty_result(self, mock_query):
        mock_query.return_value = []

        ret = list(utils.get([self.schedule_id1, self.schedule_id2]))

        self.assertEqual(mock_query.call_count, 1)

        self.assertEqual(len(ret), 0)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_gets_correct_collection(self, mock_get_collection):
        """
        make sure this operation uses the correct collection
        """
        ret = utils.get([])

        mock_get_collection.assert_called_once_with()

    def test_invalid_schedule_id(self):
        self.assertRaises(exceptions.InvalidValue, utils.get, ['notavilidid'])


class TestGetByResource(unittest.TestCase):
    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_query(self, mock_query):
        mock_query.return_value = SCHEDULES

        ret = list(utils.get_by_resource('resource1'))

        self.assertEqual(mock_query.call_count, 1)
        # there should only be 1 argument, a criteria
        self.assertEqual(len(mock_query.call_args[0]), 1)
        criteria = mock_query.call_args[0][0]
        self.assertTrue(isinstance(criteria, Criteria))
        self.assertEqual(criteria.filters, {'resource': 'resource1'})

        # three instances of ScheduledCall should be returned
        self.assertEqual(len(ret), 3)
        for schedule in ret:
            self.assertTrue(isinstance(schedule, ScheduledCall))

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_empty_result(self, mock_query):
        mock_query.return_value = []

        ret = list(utils.get_by_resource('resource1'))

        self.assertEqual(mock_query.call_count, 1)

        self.assertEqual(len(ret), 0)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_gets_correct_collection(self, mock_get_collection):
        """
        make sure this operation uses the correct collection
        """
        ret = utils.get_by_resource('resource1')

        mock_get_collection.assert_called_once_with()


class TestGetUpdatedSince(unittest.TestCase):
    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_query(self, mock_query):
        mock_query.return_value = SCHEDULES

        now = time.time()
        ret = list(utils.get_updated_since(now))

        self.assertEqual(mock_query.call_count, 1)
        # there should only be 1 argument, a criteria
        self.assertEqual(len(mock_query.call_args[0]), 1)
        criteria = mock_query.call_args[0][0]
        self.assertTrue(isinstance(criteria, Criteria))
        self.assertEqual(criteria.filters['last_updated'], {'$gt': now})
        self.assertEqual(criteria.filters['enabled'], True)

        # three instances of dict should be returned
        self.assertEqual(len(ret), 3)
        for schedule in ret:
            self.assertTrue(isinstance(schedule, dict))

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_empty_result(self, mock_query):
        mock_query.return_value = []
        now = time.time()

        ret = list(utils.get_updated_since(now))

        self.assertEqual(mock_query.call_count, 1)

        self.assertEqual(len(ret), 0)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_gets_correct_collection(self, mock_get_collection):
        """
        make sure this operation uses the correct collection
        """
        ret = utils.get_updated_since(time.time())

        mock_get_collection.assert_called_once_with()


class TestGetEnabled(unittest.TestCase):
    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_query(self, mock_query):
        mock_query.return_value = SCHEDULES

        ret = list(utils.get_enabled())

        self.assertEqual(mock_query.call_count, 1)
        # there should only be 1 argument, a criteria
        self.assertEqual(len(mock_query.call_args[0]), 1)
        criteria = mock_query.call_args[0][0]
        self.assertTrue(isinstance(criteria, Criteria))
        self.assertEqual(criteria.filters, {'enabled': True})

        # three instances of dict should be returned
        self.assertEqual(len(ret), 3)
        for schedule in ret:
            self.assertTrue(isinstance(schedule, dict))

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_empty_result(self, mock_query):
        mock_query.return_value = []

        ret = list(utils.get_enabled())

        self.assertEqual(mock_query.call_count, 1)

        self.assertEqual(len(ret), 0)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_gets_correct_collection(self, mock_get_collection):
        """
        make sure this operation uses the correct collection
        """
        ret = utils.get_enabled()

        mock_get_collection.assert_called_once_with()


class TestDelete(unittest.TestCase):
    schedule_id = str(ObjectId())

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_delete(self, mock_get_collection):
        mock_remove = mock_get_collection.return_value.remove
        mock_remove.return_value = None

        utils.delete(self.schedule_id)

        self.assertEqual(mock_remove.call_count, 1)
        # there should only be 1 argument, a criteria
        self.assertEqual(len(mock_remove.call_args[0]), 1)
        self.assertEqual(mock_remove.call_args[0][0], {'_id': ObjectId(self.schedule_id)})

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_gets_correct_collection(self, mock_get_collection):
        """
        make sure this operation uses the correct collection
        """
        ret = utils.delete(self.schedule_id)

        mock_get_collection.assert_called_once_with()

    def test_invalid_schedule_id(self):
        self.assertRaises(exceptions.InvalidValue, utils.delete, 'notavalidid')


class TestDeleteByResource(unittest.TestCase):
    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_calls_remove(self, mock_get_collection):
        mock_remove = mock_get_collection.return_value.remove
        mock_remove.return_value = None

        utils.delete_by_resource('resource1')

        mock_remove.assert_called_once_with({'resource': 'resource1'}, safe=True)


class TestUpdate(unittest.TestCase):
    schedule_id = str(ObjectId())

    @mock.patch('pickle.dumps')
    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_update(self, mock_get, mock_pickle):
        mock_find = mock_get.return_value.find_and_modify
        mock_find.return_value = SCHEDULES[0]

        ret = utils.update(self.schedule_id, {'enabled': True})

        self.assertEqual(mock_find.call_count, 1)
        self.assertEqual(len(mock_find.call_args[0]), 0)
        self.assertEqual(mock_find.call_args[1]['query'], {'_id': ObjectId(self.schedule_id)})
        self.assertTrue(mock_find.call_args[1]['update']['$set']['enabled'] is True)
        last_updated = mock_find.call_args[1]['update']['$set']['last_updated']
        # make sure the last_updated value is within the last tenth of a second
        self.assertTrue(time.time() - last_updated < .1)
        # make sure it asks for the new version of the schedule to be returned
        self.assertTrue(mock_find.call_args[1]['new'] is True)

        self.assertTrue(isinstance(ret, ScheduledCall))
        self.assertEqual(mock_pickle.call_args_list, [])

    @mock.patch('pickle.dumps')
    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_update_iso_schedule(self, mock_get, mock_pickle):
        mock_find = mock_get.return_value.find_and_modify
        mock_find.return_value = SCHEDULES[0]
        mock_pickle.return_value = "NEW_SCHEDULE"

        new_iso_sched = '2014-08-27T00:38:00Z/PT24H'

        ret = utils.update(self.schedule_id, {'iso_schedule': new_iso_sched})

        self.assertEqual(mock_find.call_count, 1)
        self.assertEqual(len(mock_find.call_args[0]), 0)
        self.assertEqual(mock_find.call_args[1]['query'], {'_id': ObjectId(self.schedule_id)})
        self.assertTrue(mock_find.call_args[1]['update']['$set']['iso_schedule'] == new_iso_sched)
        self.assertTrue(mock_find.call_args[1]['update']['$set']['schedule'] == "NEW_SCHEDULE")
        last_updated = mock_find.call_args[1]['update']['$set']['last_updated']
        # make sure the last_updated value is within the last tenth of a second
        self.assertTrue(time.time() - last_updated < .1)
        # make sure it asks for the new version of the schedule to be returned
        self.assertTrue(mock_find.call_args[1]['new'] is True)

        self.assertTrue(isinstance(ret, ScheduledCall))

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_gets_correct_collection(self, mock_get_collection):
        """
        make sure this operation uses the correct collection
        """
        mock_get_collection.return_value.find_and_modify.return_value = SCHEDULES[0]

        ret = utils.update(self.schedule_id, {'enabled': True})

        mock_get_collection.assert_called_once_with()

    def test_unknown_key(self):
        self.assertRaises(exceptions.UnsupportedValue, utils.update,
                          self.schedule_id, {'foo': 'bar'})

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_missing(self, mock_get_collection):
        # this should cause the exception to be raised
        mock_find = mock_get_collection.return_value.find_and_modify
        mock_find.return_value = None

        self.assertRaises(exceptions.MissingResource, utils.update, self.schedule_id, {'enabled': True})
        self.assertEqual(mock_find.call_count, 1)

    def test_invalid_schedule_id(self):
        self.assertRaises(exceptions.InvalidValue, utils.update, 'notavalidid', {'enabled': True})


class TestResetFailureCount(unittest.TestCase):
    schedule_id = str(ObjectId())

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_reset(self, mock_get_collection):
        mock_update = mock_get_collection.return_value.update

        utils.reset_failure_count(self.schedule_id)

        self.assertEqual(mock_update.call_count, 1)
        self.assertEqual(len(mock_update.call_args[0]), 0)
        self.assertEqual(mock_update.call_args[1]['spec'], {'_id': ObjectId(self.schedule_id)})
        self.assertEqual(mock_update.call_args[1]['document']['$set']['consecutive_failures'], 0)
        last_updated = mock_update.call_args[1]['document']['$set']['last_updated']
        # make sure the last_updated value is within the last tenth of a second
        self.assertTrue(time.time() - last_updated < .1)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_gets_correct_collection(self, mock_get_collection):
        """
        make sure this operation uses the correct collection
        """
        ret = utils.reset_failure_count(self.schedule_id)

        mock_get_collection.assert_called_once_with()

    def test_invalid_schedule_id(self):
        self.assertRaises(exceptions.InvalidValue, utils.reset_failure_count, 'notavalidid')


class TestIncrementFailureCount(unittest.TestCase):
    schedule_id = str(ObjectId())

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_update(self, mock_get_collection):
        mock_find = mock_get_collection.return_value.find_and_modify
        mock_find.return_value = SCHEDULES[0]

        utils.increment_failure_count(self.schedule_id)

        self.assertEqual(mock_find.call_count, 1)
        self.assertEqual(len(mock_find.call_args[0]), 0)
        self.assertEqual(mock_find.call_args[1]['query'], {'_id': ObjectId(self.schedule_id)})
        self.assertEqual(mock_find.call_args[1]['update']['$inc']['consecutive_failures'], 1)
        last_updated = mock_find.call_args[1]['update']['$set']['last_updated']
        # make sure the last_updated value is within the last tenth of a second
        self.assertTrue(time.time() - last_updated < .1)
        # make sure it asks for the new version of the schedule to be returned
        self.assertTrue(mock_find.call_args[1]['new'] is True)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.from_db')
    def test_not_found(self, mock_from_db, mock_get_collection):
        mock_find = mock_get_collection.return_value.find_and_modify
        mock_find.return_value = None

        utils.increment_failure_count(self.schedule_id)

        # from_db() gets called if find_and_modify returns anything.
        self.assertEqual(mock_from_db.call_count, 0)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_threshold_none(self, mock_get_collection):
        mock_find = mock_get_collection.return_value.find_and_modify
        mock_update = mock_get_collection.return_value.update
        mock_find.return_value = SCHEDULES[1]

        utils.increment_failure_count(self.schedule_id)

        self.assertEqual(mock_find.call_count, 1)

        # make sure we didn't disable the schedule
        self.assertEqual(mock_update.call_count, 0)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_schedule_already_disabled(self, mock_get_collection):
        mock_find = mock_get_collection.return_value.find_and_modify
        mock_update = mock_get_collection.return_value.update
        schedule = SCHEDULES[0].copy()
        schedule['enabled'] = False
        mock_find.return_value = schedule

        utils.increment_failure_count(self.schedule_id)

        self.assertEqual(mock_find.call_count, 1)

        # make sure we didn't disable the schedule, since it's already disabled
        self.assertEqual(mock_update.call_count, 0)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.get_collection')
    def test_disable_schedule(self, mock_get_collection):
        mock_find = mock_get_collection.return_value.find_and_modify
        mock_update = mock_get_collection.return_value.update
        schedule = SCHEDULES[0].copy()
        schedule['consecutive_failures'] = 2
        mock_find.return_value = schedule

        utils.increment_failure_count(self.schedule_id)

        self.assertEqual(mock_find.call_count, 1)

        # make sure we disable the schedule
        self.assertEqual(mock_update.call_count, 1)
        self.assertEqual(mock_update.call_args[0][0], {'_id': ObjectId(self.schedule_id)})
        self.assertTrue(mock_update.call_args[0][1]['$set']['enabled'] is False)
        last_updated = mock_update.call_args[0][1]['$set']['last_updated']
        # make sure the last_updated value is within the last tenth of a second
        self.assertTrue(time.time() - last_updated < .1)

    def test_invalid_schedule_id(self):
        self.assertRaises(exceptions.InvalidValue, utils.increment_failure_count, 'notavalidid')


SCHEDULES = [
    {
        u'_id': u'529f4bd93de3a31d0ec77338',
        u'args': [u'demo1', u'puppet_distributor'],
        u'consecutive_failures': 0,
        u'enabled': True,
        u'failure_threshold': 2,
        u'first_run': u'2013-12-04T15:35:53Z',
        u'iso_schedule': u'PT1M',
        u'kwargs': {u'overrides': {}},
        u'last_run_at': u'2013-12-17T00:35:53Z',
        u'last_updated': 1387218569.811224,
        u'next_run': u'2013-12-17T00:36:53Z',
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\nsVpassword\np17\nVV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\np19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': None,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\nsS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\ntp10\nRp11\nsb.",
        u'task': u'pulp.server.tasks.repository.publish',
        u'total_run_count': 1087,
        },
    {
        u'_id': u'529f4bd93de3a31d0ec77339',
        u'args': [u'demo2', u'puppet_distributor'],
        u'consecutive_failures': 0,
        u'enabled': True,
        u'failure_threshold': None,
        u'first_run': u'2013-12-04T15:35:53Z',
        u'iso_schedule': u'PT1M',
        u'kwargs': {u'overrides': {}},
        u'last_run_at': u'2013-12-17T00:35:53Z',
        u'last_updated': 1387218500.598727,
        u'next_run': u'2013-12-17T00:36:53Z',
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\nsVpassword\np17\nVV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\np19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': None,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\nsS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\ntp10\nRp11\nsb.",
        u'task': u'pulp.server.tasks.repository.publish',
        u'total_run_count': 1087,
        },
    {
        u'_id': u'529f4bd93de3a31d0ec77340',
        u'args': [u'demo3', u'puppet_distributor'],
        u'consecutive_failures': 0,
        u'enabled': True,
        u'failure_threshold': 2,
        u'first_run': u'2013-12-04T15:35:53Z',
        u'iso_schedule': u'PT1M',
        u'kwargs': {u'overrides': {}},
        u'last_run_at': u'2013-12-17T00:35:53Z',
        u'last_updated': 1387218501.598727,
        u'next_run': u'2013-12-17T00:36:53Z',
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\nsVpassword\np17\nVV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\np19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': 0,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\nsS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\ntp10\nRp11\nsb.",
        u'task': u'pulp.server.tasks.repository.publish',
        u'total_run_count': 1087,
    },
]
