# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import sys

try:
    from bson.objectid import ObjectId
except ImportError:
    from pymongo.objectid import ObjectId

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../common/'))

import testutil
import mock_plugins

from pulp.server import exceptions as pulp_exceptions
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.db.model.gc_repository import Repo, RepoDistributor, RepoImporter
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.schedule.cud import ScheduleManager

# schedule tests base class ----------------------------------------------------

class ScheduleTests(testutil.PulpCoordinatorTest):

    def setUp(self):
        super(ScheduleTests, self).setUp()

        mock_plugins.install()
        self._repo_manager = managers_factory.repo_manager()
        self._distributor_manager = managers_factory.repo_distributor_manager()
        self._importer_manager = managers_factory.repo_importer_manager()

        self.repo_id = 'scheduled-repo'
        self.distributor_type_id = 'mock-distributor'
        self.distributor_id = 'scheduled-distributor'
        self.importer_type_id = 'mock-importer'

        self._repo_manager.create_repo(self.repo_id)
        self._distributor_manager.add_distributor(self.repo_id, self.distributor_type_id, {}, False, distributor_id=self.distributor_id)
        self._importer_manager.set_importer(self.repo_id, self.importer_type_id, {})

        self.schedule_manager = ScheduleManager()

    def tearDown(self):
        super(ScheduleTests, self).tearDown()
        mock_plugins.reset()
        self._repo_manager = None
        self._distributor_manager = None
        self._importer_manager = None
        self.schedule_manager = None

    def clean(self):
        super(ScheduleTests, self).clean()
        Repo.get_collection().remove(safe=True)
        RepoDistributor.get_collection().remove(safe=True)
        RepoImporter.get_collection().remove(safe=True)
        ScheduledCall.get_collection().remove(safe=True)

# schedule manager tests -------------------------------------------------------

class ScheduleManagerTests(testutil.PulpTest):

    def test_instantiation(self):
        schedule_manager = ScheduleManager()

    def test_validate_valid_keys(self):
        valid_keys = ('one', 'two', 'three')
        options = {'one': 1, 'two': 2, 'three': 3}
        schedule_manager = ScheduleManager()
        try:
            schedule_manager._validate_keys(options, valid_keys)
        except Exception, e:
            self.fail(str(e))

    def test_validate_invalid_superfluous_keys(self):
        valid_keys = ('yes', 'ok')
        options = {'ok': 1, 'not': 0}
        schedule_manager = ScheduleManager()
        self.assertRaises(pulp_exceptions.InvalidValue,
                          schedule_manager._validate_keys,
                          options, valid_keys)

    def test_validate_invalid_missing_keys(self):
        valid_keys = ('me', 'me_too')
        options = {'me': 'only'}
        schedule_manager = ScheduleManager()
        self.assertRaises(pulp_exceptions.MissingValue,
                          schedule_manager._validate_keys,
                          options, valid_keys, True)

# sync schedule tests ----------------------------------------------------------

class ScheduledSyncTests(ScheduleTests):

    def test_create_schedule(self):
        sync_options = {'override_config': {}}
        schedule_data = {'schedule': 'R1/P1DT'}
        schedule_id = self.schedule_manager.create_sync_schedule(self.repo_id,
                                                                 self.importer_type_id,
                                                                 sync_options,
                                                                 schedule_data)
        collection = ScheduledCall.get_collection()
        schedule = collection.find_one(ObjectId(schedule_id))
        self.assertFalse(schedule is None)
        self.assertTrue(schedule_id == str(schedule['_id']))

        schedule_list = self._importer_manager.list_sync_schedules(self.repo_id)
        self.assertTrue(schedule_id in schedule_list)

    def test_delete_schedule(self):
        sync_options = {'override_config': {}}
        schedule_data = {'schedule': 'R1/P1DT'}
        schedule_id = self.schedule_manager.create_sync_schedule(self.repo_id,
                                                                 self.importer_type_id,
                                                                 sync_options,
                                                                 schedule_data)
        collection = ScheduledCall.get_collection()
        schedule = collection.find_one(ObjectId(schedule_id))
        self.assertFalse(schedule is None)

        self.schedule_manager.delete_sync_schedule(self.repo_id,
                                                   self.importer_type_id,
                                                   schedule_id)
        schedule = collection.find_one(ObjectId(schedule_id))
        self.assertTrue(schedule is None)

        schedule_list = self._importer_manager.list_sync_schedules(self.repo_id)
        self.assertFalse(schedule_id in schedule_list)

    def test_update_schedule(self):
        sync_options = {'override_config': {}}
        schedule_data = {'schedule': 'R1/P1DT'}
        schedule_id = self.schedule_manager.create_sync_schedule(self.repo_id,
                                                                 self.importer_type_id,
                                                                 sync_options,
                                                                 schedule_data)
        scheduler = dispatch_factory.scheduler()
        schedule_report = scheduler.get(schedule_id)
        self.assertTrue(schedule_id == schedule_report['_id'])
        self.assertTrue(sync_options['override_config'] == schedule_report['call_request'].kwargs['sync_config_override'])
        self.assertTrue(schedule_data['schedule'] == schedule_report['schedule'])

        new_sync_options = {'override_config': {'option_1': 'new_option'}}
        new_schedule_data = {'schedule': 'R4/PT24H', 'failure_threshold': 4}
        self.schedule_manager.update_sync_schedule(self.repo_id,
                                                   self.importer_type_id,
                                                   schedule_id,
                                                   new_sync_options,
                                                   new_schedule_data)
        schedule_report = scheduler.get(schedule_id)
        self.assertTrue(schedule_id == schedule_report['_id'])
        self.assertTrue(new_sync_options['override_config'] == schedule_report['call_request'].kwargs['sync_config_override'])
        self.assertTrue(new_schedule_data['schedule'] == schedule_report['schedule'])
        self.assertTrue(new_schedule_data['failure_threshold'] == schedule_report['failure_threshold'])

# publish schedule tests -------------------------------------------------------

class ScheduledPublishTests(ScheduleTests):

    def test_create_schedule(self):
        publish_options = {'override_config': {}}
        schedule_data = {'schedule': 'R1/P1DT'}
        schedule_id = self.schedule_manager.create_publish_schedule(self.repo_id,
                                                                    self.distributor_id,
                                                                    publish_options,
                                                                    schedule_data)
        collection = ScheduledCall.get_collection()
        schedule = collection.find_one(ObjectId(schedule_id))
        self.assertFalse(schedule is None)
        self.assertTrue(schedule_id == str(schedule['_id']))

        schedule_list = self._distributor_manager.list_publish_schedules(self.repo_id,
                                                                         self.distributor_id)
        self.assertTrue(schedule_id in schedule_list)

    def test_delete_schedule(self):
        publish_options = {'override_config': {}}
        schedule_data = {'schedule': 'R1/P1DT'}
        schedule_id = self.schedule_manager.create_publish_schedule(self.repo_id,
                                                                    self.distributor_id,
                                                                    publish_options,
                                                                    schedule_data)
        collection = ScheduledCall.get_collection()
        schedule = collection.find_one(ObjectId(schedule_id))
        self.assertFalse(schedule is None)

        self.schedule_manager.delete_publish_schedule(self.repo_id,
                                                      self.distributor_id,
                                                      schedule_id)
        schedule = collection.find_one(ObjectId(schedule_id))
        self.assertTrue(schedule is None)

        schedule_list = self._distributor_manager.list_publish_schedules(self.repo_id,
                                                                         self.distributor_id)
        self.assertFalse(schedule_id in schedule_list)

    def test_update_schedule(self):
        publish_options = {'override_config': {}}
        schedule_data = {'schedule': 'R1/P1DT'}
        schedule_id = self.schedule_manager.create_publish_schedule(self.repo_id,
                                                                    self.distributor_id,
                                                                    publish_options,
                                                                    schedule_data)
        scheduler = dispatch_factory.scheduler()
        schedule_report = scheduler.get(schedule_id)
        self.assertTrue(schedule_id == schedule_report['_id'])
        self.assertTrue(publish_options['override_config'] == schedule_report['call_request'].kwargs['publish_config_override'])
        self.assertTrue(schedule_data['schedule'] == schedule_report['schedule'])

        new_publish_options = {'override_config': {'option_1': 'new_option'}}
        new_schedule_data = {'schedule': 'R4/PT24H', 'failure_threshold': 4}
        self.schedule_manager.update_publish_schedule(self.repo_id,
                                                      self.distributor_id,
                                                      schedule_id,
                                                      new_publish_options,
                                                      new_schedule_data)
        schedule_report = scheduler.get(schedule_id)
        self.assertTrue(schedule_id == schedule_report['_id'])
        self.assertTrue(new_publish_options['override_config'] == schedule_report['call_request'].kwargs['publish_config_override'])
        self.assertTrue(new_schedule_data['schedule'] == schedule_report['schedule'])
        self.assertTrue(new_schedule_data['failure_threshold'] == schedule_report['failure_threshold'])

