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

import functools
import itertools
import unittest

import mock

from pulp.server import exceptions
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.db.model.repository import RepoImporter, RepoDistributor
from pulp.server.managers.factory import initialize
from pulp.server.managers.schedule.repo import RepoSyncScheduleManager, RepoPublishScheduleManager

initialize()


class TestSyncList(unittest.TestCase):
    @mock.patch.object(RepoSyncScheduleManager, 'validate_importer')
    @mock.patch('pulp.server.managers.schedule.utils.get_by_resource')
    def test_validate_importer(self, mock_get_by_resource, mock_validate_importer):
        RepoSyncScheduleManager.list('repo1', 'importer1')

        mock_validate_importer.assert_called_once_with('repo1', 'importer1')

    @mock.patch.object(RepoSyncScheduleManager, 'validate_importer', return_value=None)
    @mock.patch('pulp.server.managers.schedule.utils.get_by_resource')
    def test_list(self, mock_get_by_resource, mock_validate_importer):
        ret = RepoSyncScheduleManager.list('repo1', 'importer1')

        mock_get_by_resource.assert_called_once_with(RepoImporter.build_resource_tag('repo1', 'importer1'))
        self.assertTrue(ret is mock_get_by_resource.return_value)


class TestSyncCreate(unittest.TestCase):
    repo = 'repo1'
    importer = 'importer1'
    options = {'override_config': {}}
    schedule = 'PT1M'

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_validate_importer(self, mock_get_importer):
        mock_get_importer.return_value = {'id': 'foo'}

        self.assertRaises(exceptions.MissingResource, RepoSyncScheduleManager.create,
                          self.repo, self.importer, self.options, self.schedule)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.save')
    @mock.patch.object(RepoSyncScheduleManager, 'validate_importer', return_value=None)
    @mock.patch('pulp.server.managers.schedule.utils.validate_initial_schedule_options')
    @mock.patch('pulp.server.managers.schedule.utils.validate_keys')
    def test_utils_validation(self, mock_validate_keys, mock_validate_options,
                             mock_validate_importer, mock_save):
        RepoSyncScheduleManager.create(self.repo, self.importer, self.options, self.schedule)

        mock_validate_keys.assert_called_once_with(self.options, ('override_config',))
        mock_validate_options.assert_called_once_with(self.schedule, None, True)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.save')
    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_save(self, mock_get_importer, mock_save):
        mock_get_importer.return_value = {'id': 'importer1'}

        ret = RepoSyncScheduleManager.create(self.repo, self.importer, self.options,
                                             self.schedule, 3, False)

        mock_save.assert_called_once_with()
        self.assertTrue(isinstance(ret, ScheduledCall))
        self.assertEqual(ret.iso_schedule, self.schedule)
        self.assertEqual(ret.failure_threshold, 3)
        self.assertTrue(ret.enabled is False)

    @mock.patch('pulp.server.db.model.base.ObjectId', return_value='myobjectid')
    @mock.patch('pulp.server.managers.schedule.utils.delete')
    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.save')
    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_cleanup(self, mock_get_importer, mock_save, mock_delete, mock_objectid):
        mock_get_importer.side_effect = [{'id': 'importer1'}, {'id': 'someotherimporter'}]

        self.assertRaises(exceptions.MissingResource, RepoSyncScheduleManager.create,
                          self.repo, self.importer, self.options, self.schedule)

        mock_delete.assert_called_once_with('myobjectid')


class TestSyncUpdate(unittest.TestCase):
    repo = 'repo1'
    importer = 'importer1'
    schedule_id = 'schedule1'
    override = {'override_config': {'foo': 'bar'}}
    updates = {'enabled': True}

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_validate_importer(self, mock_get_importer):
        mock_get_importer.return_value = {'id': 'foo'}

        self.assertRaises(exceptions.MissingResource, RepoSyncScheduleManager.update,
                          self.repo, self.importer, self.schedule_id, self.updates)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.schedule.utils.validate_updated_schedule_options')
    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_validate_options(self, mock_get_importer, mock_validate_options, mock_update):
        mock_get_importer.return_value = {'id': self.importer}

        RepoSyncScheduleManager.update(self.repo, self.importer, self.schedule_id, self.updates)

        mock_validate_options.assert_called_once_with(self.updates)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_update(self, mock_get_importer, mock_update):
        mock_get_importer.return_value = {'id': self.importer}

        ret = RepoSyncScheduleManager.update(self.repo, self.importer,
                                             self.schedule_id, self.updates)

        mock_update.assert_called_once_with(self.schedule_id, self.updates)
        # make sure it passes through the return value from utils.update
        self.assertEqual(ret, mock_update.return_value)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_update_overrides(self, mock_get_importer, mock_update):
        mock_get_importer.return_value = {'id': self.importer}

        RepoSyncScheduleManager.update(self.repo, self.importer, self.schedule_id,
                                       {'override_config': {'foo': 'bar'}})

        mock_update.assert_called_once_with(self.schedule_id,
                                            {'kwargs': {'overrides': {'foo': 'bar'}}})


class TestSyncDelete(unittest.TestCase):
    repo = 'repo1'
    importer = 'importer1'
    schedule_id = 'schedule1'

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_validate_importer(self, mock_get_importer):
        mock_get_importer.return_value = {'id': 'foo'}

        self.assertRaises(exceptions.MissingResource, RepoSyncScheduleManager.delete,
                          self.repo, self.importer, self.schedule_id)

    @mock.patch('pulp.server.managers.schedule.utils.delete')
    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_delete(self, mock_get_importer, mock_delete):
        mock_get_importer.return_value = {'id': self.importer}

        RepoSyncScheduleManager.delete(self.repo, self.importer, self.schedule_id)

        mock_delete.assert_called_once_with(self.schedule_id)


class TestSyncDeleteByImporterId(unittest.TestCase):
    repo = 'repo1'
    importer = 'importer1'

    @mock.patch('pulp.server.managers.schedule.utils.delete_by_resource')
    def test_calls_delete_resource(self, mock_delete_by):
        resource = RepoImporter.build_resource_tag(self.repo, self.importer)

        RepoSyncScheduleManager.delete_by_importer_id(self.repo, self.importer)

        mock_delete_by.assert_called_once_with(resource)


class TestValidateImporter(unittest.TestCase):
    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_matching_importer(self, mock_get_importer):
        mock_get_importer.return_value = {'id': 'importer1'}

        RepoSyncScheduleManager.validate_importer('repo1', 'importer1')

        mock_get_importer.assert_called_once_with('repo1')

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer')
    def test_wrong_importer(self, mock_get_importer):
        mock_get_importer.return_value = {'id': 'wrong_importer'}

        self.assertRaises(exceptions.MissingResource,
                          RepoSyncScheduleManager.validate_importer, 'repo1', 'importer1')


class TestPublishList(unittest.TestCase):
    @mock.patch.object(RepoPublishScheduleManager, 'validate_distributor')
    @mock.patch('pulp.server.managers.schedule.utils.get_by_resource')
    def test_validate_distributor(self, mock_get_by_resource, mock_validate_distributor):
        RepoPublishScheduleManager.list('repo1', 'distributor1')

        mock_validate_distributor.assert_called_once_with('repo1', 'distributor1')

    @mock.patch.object(RepoPublishScheduleManager, 'validate_distributor', return_value=None)
    @mock.patch('pulp.server.managers.schedule.utils.get_by_resource')
    def test_list(self, mock_get_by_resource, mock_validate_distributor):
        ret = RepoPublishScheduleManager.list('repo1', 'distributor1')

        mock_get_by_resource.assert_called_once_with(RepoDistributor.build_resource_tag('repo1', 'distributor1'))
        self.assertTrue(ret is mock_get_by_resource.return_value)


class TestPublishCreate(unittest.TestCase):
    repo = 'repo1'
    distributor = 'distributor1'
    options = {'override_config': {}}
    schedule = 'PT1M'

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_validate_distributor(self, mock_get_distributor):
        mock_get_distributor.side_effect = exceptions.MissingResource

        self.assertRaises(exceptions.MissingResource, RepoPublishScheduleManager.create,
                          self.repo, self.distributor, self.options, self.schedule)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.save')
    @mock.patch.object(RepoPublishScheduleManager, 'validate_distributor', return_value=None)
    @mock.patch('pulp.server.managers.schedule.utils.validate_initial_schedule_options')
    @mock.patch('pulp.server.managers.schedule.utils.validate_keys')
    def test_utils_validation(self, mock_validate_keys, mock_validate_options,
                              mock_validate_distributor, mock_save):
        RepoPublishScheduleManager.create(self.repo, self.distributor, self.options, self.schedule)

        mock_validate_keys.assert_called_once_with(self.options, ('override_config',))
        mock_validate_options.assert_called_once_with(self.schedule, None, True)

    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.save')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_save(self, mock_get_distributor, mock_save):
        mock_get_distributor.return_value = {'id': 'distributor1'}

        ret = RepoPublishScheduleManager.create(self.repo, self.distributor, self.options,
                                                self.schedule, 3, False)

        mock_save.assert_called_once_with()
        self.assertTrue(isinstance(ret, ScheduledCall))
        self.assertEqual(ret.iso_schedule, self.schedule)
        self.assertEqual(ret.failure_threshold, 3)
        self.assertTrue(ret.enabled is False)

    @mock.patch('pulp.server.db.model.base.ObjectId', return_value='myobjectid')
    @mock.patch('pulp.server.managers.schedule.utils.delete')
    @mock.patch('pulp.server.db.model.dispatch.ScheduledCall.save')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_cleanup(self, mock_get_distributor, mock_save, mock_delete, mock_objectid):
        def fake_get(count, *args, **kwargs):
            """
            Return legit data on the first call, and raise an exception on the
            second, to simulate the distributor being deleted while a schedule
            create operation is happening.

            :type count: itertools.count
            """
            if next(count) == 0:
                return {'id': 'distributor1'}
            else:
                raise exceptions.MissingResource

        count = itertools.count()
        mock_get_distributor.side_effect = functools.partial(fake_get, count)

        self.assertRaises(exceptions.MissingResource, RepoPublishScheduleManager.create,
                          self.repo, self.distributor, self.options, self.schedule)

        mock_delete.assert_called_once_with('myobjectid')


class TestPublishUpdate(unittest.TestCase):
    repo = 'repo1'
    distributor = 'distributor1'
    schedule_id = 'schedule1'
    override = {'override_config': {'foo': 'bar'}}
    updates = {'enabled': True}

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_validate_distributor(self, mock_get_distributor):
        mock_get_distributor.side_effect = exceptions.MissingResource

        self.assertRaises(exceptions.MissingResource, RepoPublishScheduleManager.update,
                          self.repo, self.distributor, self.schedule_id, self.updates)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.schedule.utils.validate_updated_schedule_options')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_validate_options(self, mock_get_distributor, mock_validate_options, mock_update):
        mock_get_distributor.return_value = {'id': self.distributor}

        RepoPublishScheduleManager.update(self.repo, self.distributor, self.schedule_id, self.updates)

        mock_validate_options.assert_called_once_with(self.updates)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_update(self, mock_get_distributor, mock_update):
        mock_get_distributor.return_value = {'id': self.distributor}

        ret = RepoPublishScheduleManager.update(self.repo, self.distributor, self.schedule_id, self.updates)

        mock_update.assert_called_once_with(self.schedule_id, self.updates)
        # make sure it passes through the return value from utils.update
        self.assertEqual(ret, mock_update.return_value)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_update_overrides(self, mock_get_distributor, mock_update):
        mock_get_distributor.return_value = None

        RepoPublishScheduleManager.update(self.repo, self.distributor, self.schedule_id,
                                       {'override_config': {'foo': 'bar'}})

        mock_update.assert_called_once_with(self.schedule_id,
                                            {'kwargs': {'overrides': {'foo': 'bar'}}})


class TestPublishDelete(unittest.TestCase):
    repo = 'repo1'
    distributor = 'distributor1'
    schedule_id = 'schedule1'

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_validate_distributor(self, mock_get_distributor):
        mock_get_distributor.side_effect = exceptions.MissingResource

        self.assertRaises(exceptions.MissingResource, RepoPublishScheduleManager.delete,
                          self.repo, self.distributor, self.schedule_id)

    @mock.patch('pulp.server.managers.schedule.utils.delete')
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_delete(self, mock_get_distributor, mock_delete):
        mock_get_distributor.return_value = None

        RepoPublishScheduleManager.delete(self.repo, self.distributor, self.schedule_id)

        mock_delete.assert_called_once_with(self.schedule_id)


class TestPublishDeleteByImporterId(unittest.TestCase):
    repo = 'repo1'
    distributor = 'distributor1'

    @mock.patch('pulp.server.managers.schedule.utils.delete_by_resource')
    def test_calls_delete_resource(self, mock_delete_by):
        resource = RepoDistributor.build_resource_tag(self.repo, self.distributor)

        RepoPublishScheduleManager.delete_by_distributor_id(self.repo, self.distributor)

        mock_delete_by.assert_called_once_with(resource)


class TestValidateDistributor(unittest.TestCase):
    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_matching_distributor(self, mock_get_distributor):
        mock_get_distributor.return_value = None

        RepoPublishScheduleManager.validate_distributor('repo1', 'distributor1')

        mock_get_distributor.assert_called_once_with('repo1', 'distributor1')

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.get_distributor')
    def test_wrong_distributor(self, mock_get_distributor):
        mock_get_distributor.side_effect = exceptions.MissingResource

        self.assertRaises(exceptions.MissingResource,
                          RepoPublishScheduleManager.validate_distributor, 'repo1', 'distributor1')


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
