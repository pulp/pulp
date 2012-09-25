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

import copy

import base
import mock_plugins

from pulp.server import exceptions as pulp_exceptions
from pulp.server.compat import ObjectId
from pulp.server.db.model.consumer import Consumer, ConsumerHistoryEvent
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.db.model.repository import Repo, RepoDistributor, RepoImporter
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.schedule import utils as schedule_utils
from pulp.server.managers.schedule.aggregate import AggregateScheduleManager

# schedule tests base class ----------------------------------------------------

class ScheduleTests(base.PulpAsyncServerTests):

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

        self.schedule_manager = AggregateScheduleManager()

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

class ScheduleManagerTests(base.PulpAsyncServerTests):

    def test_instantiation(self):
        schedule_manager = AggregateScheduleManager()

    def test_validate_valid_keys(self):
        valid_keys = ('one', 'two', 'three')
        options = {'one': 1, 'two': 2, 'three': 3}
        schedule_manager = AggregateScheduleManager()
        try:
            schedule_utils.validate_keys(options, valid_keys)
        except Exception, e:
            self.fail(str(e))

    def test_validate_invalid_superfluous_keys(self):
        valid_keys = ('yes', 'ok')
        options = {'ok': 1, 'not': 0}
        schedule_manager = AggregateScheduleManager()
        self.assertRaises(pulp_exceptions.InvalidValue,
                          schedule_utils.validate_keys,
                          options, valid_keys)

    def test_validate_invalid_missing_keys(self):
        valid_keys = ('me', 'me_too')
        options = {'me': 'only'}
        schedule_manager = AggregateScheduleManager()
        self.assertRaises(pulp_exceptions.MissingValue,
                          schedule_utils.validate_keys,
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

# unit install schedule tests --------------------------------------------------

_TEST_UNITS = [
    {'type_id': 'mock-type',
     'unit_key': {'id': 'mongodb'}},
    {'type_id': 'mock-type',
     'unit_key': {'id': 'cassandra'}},
    {'type_id': 'mock-type',
     'unit_key': {'id': 'tokyo-cabinet'}},
    {'type_id': 'mock-type',
     'unit_key': {'id': 'couchdb'}}]


class ScheduledUnitInstallTests(ScheduleTests):

    def setUp(self):
        super(ScheduledUnitInstallTests, self).setUp()
        self.consumer_id = 'test-consumer'
        self._consumer_manager = managers_factory.consumer_manager()
        self._consumer_manager.register(self.consumer_id)

    def tearDown(self):
        super(ScheduledUnitInstallTests, self).tearDown()
        self.consumer_id = None
        self._consumer_manager = None

    def clean(self):
        super(ScheduledUnitInstallTests, self).clean()
        Consumer.get_collection().remove(safe=True)
        ConsumerHistoryEvent.get_collection().remove(safe=True)

    # test methods -------------------------------------------------------------

    def test_create_schedule(self):
        install_options = {'options': {}}
        schedule_data = {'schedule': 'R1/P1DT'}

        schedule_id = self.schedule_manager.create_unit_install_schedule(self.consumer_id, _TEST_UNITS, install_options, schedule_data)

        scheduler = dispatch_factory.scheduler()
        scheduled_call = scheduler.get(schedule_id)

        self.assertFalse(scheduled_call is None)
        self.assertTrue(schedule_data['schedule'] == scheduled_call['schedule'])
        self.assertTrue(self.consumer_id in scheduled_call['call_request'].args)
        self.assertTrue(_TEST_UNITS == scheduled_call['call_request'].kwargs['units'])
        self.assertTrue(install_options['options'] == scheduled_call['call_request'].kwargs['options'])

    def test_create_schedule_invalid_consumer(self):
        install_options = {'options': {}}
        schedule_data = {'schedule': 'R1/P1DT'}

        self.assertRaises(pulp_exceptions.MissingResource,
                          self.schedule_manager.create_unit_install_schedule,
                          'invalid-consumer', _TEST_UNITS, install_options, schedule_data)

    def test_create_schedule_missing_schedule(self):
        self.assertRaises(pulp_exceptions.MissingValue,
                          self.schedule_manager.create_unit_install_schedule,
                          self.consumer_id, _TEST_UNITS, {}, {})

    def test_delete_schedule(self):
        schedule_data = {'schedule': 'R1/P1DT'}
        schedule_id = self.schedule_manager.create_unit_install_schedule(self.consumer_id, _TEST_UNITS, {}, schedule_data)

        scheduler = dispatch_factory.scheduler()
        scheduled_call = scheduler.get(schedule_id)

        self.assertFalse(scheduled_call is None)

        self.schedule_manager.delete_unit_install_schedule(self.consumer_id, schedule_id)

        self.assertRaises(pulp_exceptions.MissingResource, scheduler.get, schedule_id)

    def test_update_schedule(self):
        units = copy.copy(_TEST_UNITS)
        install_options = {'options': {}}
        schedule_data = {'schedule': 'R1/P1DT'}

        schedule_id = self.schedule_manager.create_unit_install_schedule(self.consumer_id, units, install_options, schedule_data)

        scheduler = dispatch_factory.scheduler()
        scheduled_call = scheduler.get(schedule_id)

        self.assertFalse(scheduled_call is None)
        self.assertTrue(schedule_data['schedule'] == scheduled_call['schedule'])
        self.assertTrue(self.consumer_id in scheduled_call['call_request'].args)
        self.assertTrue(units == scheduled_call['call_request'].kwargs['units'])
        self.assertTrue(install_options['options'] == scheduled_call['call_request'].kwargs['options'])

        units.append({'type_id': 'mock-type', 'unit_key': {'id': 'redis'}})
        install_options['options'] = {'option': 'value'}
        schedule_data['schedule'] = 'R3/P1DT'

        self.schedule_manager.update_unit_install_schedule(self.consumer_id, schedule_id, units, install_options, schedule_data)

        updated_call = scheduler.get(schedule_id)

        self.assertFalse(updated_call is None)
        self.assertTrue(schedule_data['schedule'] == updated_call['schedule'], '%s != %s' % (schedule_data['schedule'], updated_call['schedule']))
        self.assertTrue(self.consumer_id in updated_call['call_request'].args)
        self.assertTrue(units == updated_call['call_request'].kwargs['units'])
        self.assertTrue(install_options['options'] == updated_call['call_request'].kwargs['options'])

# scheduled unit update tests --------------------------------------------------

class ScheduledUnitUpdateTests(ScheduleTests):

    def setUp(self):
        super(ScheduledUnitUpdateTests, self).setUp()
        self.consumer_id = 'test-consumer'
        self._consumer_manager = managers_factory.consumer_manager()
        self._consumer_manager.register(self.consumer_id)

    def tearDown(self):
        super(ScheduledUnitUpdateTests, self).tearDown()
        self.consumer_id = None
        self._consumer_manager = None

    def clean(self):
        super(ScheduledUnitUpdateTests, self).clean()
        Consumer.get_collection().remove(safe=True)
        ConsumerHistoryEvent.get_collection().remove(safe=True)

   # test methods -------------------------------------------------------------

    def test_create_schedule(self):
        update_options = {'options': {}}
        schedule_data = {'schedule': 'R1/P1DT'}

        schedule_id = self.schedule_manager.create_unit_update_schedule(self.consumer_id, _TEST_UNITS, update_options, schedule_data)

        scheduler = dispatch_factory.scheduler()
        scheduled_call = scheduler.get(schedule_id)

        self.assertFalse(scheduled_call is None)
        self.assertTrue(schedule_data['schedule'] == scheduled_call['schedule'])
        self.assertTrue(self.consumer_id in scheduled_call['call_request'].args)
        self.assertTrue(_TEST_UNITS == scheduled_call['call_request'].kwargs['units'])
        self.assertTrue(update_options['options'] == scheduled_call['call_request'].kwargs['options'])

    def test_delete_schedule(self):
        schedule_data = {'schedule': 'R1/P1DT'}
        schedule_id = self.schedule_manager.create_unit_update_schedule(self.consumer_id, _TEST_UNITS, {}, schedule_data)

        scheduler = dispatch_factory.scheduler()
        scheduled_call = scheduler.get(schedule_id)

        self.assertFalse(scheduled_call is None)

        self.schedule_manager.delete_unit_update_schedule(self.consumer_id, schedule_id)

        self.assertRaises(pulp_exceptions.MissingResource, scheduler.get, schedule_id)

    def test_update_schedule(self):
        units = copy.copy(_TEST_UNITS)
        update_options = {'options': {}}
        schedule_data = {'schedule': 'R1/P1DT'}

        schedule_id = self.schedule_manager.create_unit_update_schedule(self.consumer_id, units, update_options, schedule_data)

        scheduler = dispatch_factory.scheduler()
        scheduled_call = scheduler.get(schedule_id)

        self.assertFalse(scheduled_call is None)
        self.assertTrue(schedule_data['schedule'] == scheduled_call['schedule'])
        self.assertTrue(self.consumer_id in scheduled_call['call_request'].args)
        self.assertTrue(units == scheduled_call['call_request'].kwargs['units'])
        self.assertTrue(update_options['options'] == scheduled_call['call_request'].kwargs['options'])

        units.append({'type_id': 'mock-type', 'unit_key': {'id': 'redis'}})
        update_options['options'] = {'option': 'value'}
        schedule_data['schedule'] = 'R3/P1DT'

        self.schedule_manager.update_unit_update_schedule(self.consumer_id, schedule_id, units, update_options, schedule_data)

        updated_call = scheduler.get(schedule_id)

        self.assertFalse(updated_call is None)
        self.assertTrue(schedule_data['schedule'] == updated_call['schedule'], '%s != %s' % (schedule_data['schedule'], updated_call['schedule']))
        self.assertTrue(self.consumer_id in updated_call['call_request'].args)
        self.assertTrue(units == updated_call['call_request'].kwargs['units'])
        self.assertTrue(update_options['options'] == updated_call['call_request'].kwargs['options'])

# scheduled unit uninstall tests -----------------------------------------------

class ScheduledUnitUninstallTests(ScheduleTests):

    def setUp(self):
        super(ScheduledUnitUninstallTests, self).setUp()
        self.consumer_id = 'test-consumer'
        self._consumer_manager = managers_factory.consumer_manager()
        self._consumer_manager.register(self.consumer_id)

    def tearDown(self):
        super(ScheduledUnitUninstallTests, self).tearDown()
        self.consumer_id = None
        self._consumer_manager = None

    def clean(self):
        super(ScheduledUnitUninstallTests, self).clean()
        Consumer.get_collection().remove(safe=True)
        ConsumerHistoryEvent.get_collection().remove(safe=True)

    # test methods -------------------------------------------------------------

    def test_create_schedule(self):
        uninstall_options = {'options': {}}
        schedule_data = {'schedule': 'R1/P1DT'}

        schedule_id = self.schedule_manager.create_unit_uninstall_schedule(self.consumer_id, _TEST_UNITS, uninstall_options, schedule_data)

        scheduler = dispatch_factory.scheduler()
        scheduled_call = scheduler.get(schedule_id)

        self.assertFalse(scheduled_call is None)
        self.assertTrue(schedule_data['schedule'] == scheduled_call['schedule'])
        self.assertTrue(self.consumer_id in scheduled_call['call_request'].args)
        self.assertTrue(_TEST_UNITS == scheduled_call['call_request'].kwargs['units'])
        self.assertTrue(uninstall_options['options'] == scheduled_call['call_request'].kwargs['options'])

    def test_delete_schedule(self):
        schedule_data = {'schedule': 'R1/P1DT'}
        schedule_id = self.schedule_manager.create_unit_uninstall_schedule(self.consumer_id, _TEST_UNITS, {}, schedule_data)

        scheduler = dispatch_factory.scheduler()
        scheduled_call = scheduler.get(schedule_id)

        self.assertFalse(scheduled_call is None)

        self.schedule_manager.delete_unit_uninstall_schedule(self.consumer_id, schedule_id)

        self.assertRaises(pulp_exceptions.MissingResource, scheduler.get, schedule_id)

    def test_update_schedule(self):
        units = copy.copy(_TEST_UNITS)
        uninstall_options = {'options': {}}
        schedule_data = {'schedule': 'R1/P1DT'}

        schedule_id = self.schedule_manager.create_unit_uninstall_schedule(self.consumer_id, units, uninstall_options, schedule_data)

        scheduler = dispatch_factory.scheduler()
        scheduled_call = scheduler.get(schedule_id)

        self.assertFalse(scheduled_call is None)
        self.assertTrue(schedule_data['schedule'] == scheduled_call['schedule'])
        self.assertTrue(self.consumer_id in scheduled_call['call_request'].args)
        self.assertTrue(units == scheduled_call['call_request'].kwargs['units'])
        self.assertTrue(uninstall_options['options'] == scheduled_call['call_request'].kwargs['options'])

        units.append({'type_id': 'mock-type', 'unit_key': {'id': 'redis'}})
        uninstall_options['options'] = {'option': 'value'}
        schedule_data['schedule'] = 'R3/P1DT'

        self.schedule_manager.update_unit_uninstall_schedule(self.consumer_id, schedule_id, units, uninstall_options, schedule_data)

        updated_call = scheduler.get(schedule_id)

        self.assertFalse(updated_call is None)
        self.assertTrue(schedule_data['schedule'] == updated_call['schedule'], '%s != %s' % (schedule_data['schedule'], updated_call['schedule']))
        self.assertTrue(self.consumer_id in updated_call['call_request'].args)
        self.assertTrue(units == updated_call['call_request'].kwargs['units'])
        self.assertTrue(uninstall_options['options'] == updated_call['call_request'].kwargs['options'])

