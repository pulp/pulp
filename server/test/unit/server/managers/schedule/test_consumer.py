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

import unittest

import mock
from pulp.server.db.model.consumer import Consumer
from pulp.server.db.model.dispatch import ScheduledCall

from pulp.server.exceptions import MissingResource, InvalidValue
from pulp.server.managers.factory import initialize
from pulp.server.managers.schedule.consumer import ConsumerScheduleManager, UNIT_INSTALL_ACTION, UNIT_UPDATE_ACTION, ACTIONS_TO_TASKS


initialize()


class TestValidate(unittest.TestCase):
    def setUp(self):
        super(TestValidate, self).setUp()
        self.manager = ConsumerScheduleManager()

    @mock.patch('pulp.server.managers.consumer.cud.ConsumerManager.get_consumer')
    def test_calls_get_consumer(self, mock_get):
        self.manager._validate_consumer('foo')

        mock_get.assert_called_once_with('foo')

    @mock.patch('pulp.server.db.model.base.Model.get_collection')
    def test_raises_missing(self, mock_get_collection):
        # mock another layer down to verify manager integration
        mock_get_collection.return_value.find_one.side_effect = MissingResource

        self.assertRaises(MissingResource, self.manager._validate_consumer, 'foo')


class TestGet(unittest.TestCase):
    def setUp(self):
        super(TestGet, self).setUp()
        self.manager = ConsumerScheduleManager()
        self.calls = [
            ScheduledCall('PT1H', ACTIONS_TO_TASKS[UNIT_INSTALL_ACTION]),
            ScheduledCall('PT4H', ACTIONS_TO_TASKS[UNIT_UPDATE_ACTION])
        ]

    @mock.patch('pulp.server.managers.schedule.utils.get_by_resource')
    def test_no_action(self, mock_get_by_resource):
        mock_get_by_resource.return_value = self.calls

        result = self.manager.get('consumer1')

        mock_get_by_resource.assert_called_once_with(Consumer.build_resource_tag('consumer1'))
        self.assertEqual(result, self.calls)

    @mock.patch('pulp.server.managers.schedule.utils.get_by_resource')
    def test_with_action(self, mock_get_by_resource):
        mock_get_by_resource.return_value = self.calls

        result = self.manager.get('consumer1', UNIT_INSTALL_ACTION)

        mock_get_by_resource.assert_called_once_with(Consumer.build_resource_tag('consumer1'))
        self.assertEqual(list(result), self.calls[:1])


class TestCreate(unittest.TestCase):
    def setUp(self):
        super(TestCreate, self).setUp()
        self.manager = ConsumerScheduleManager()
        self.units = [
            {'type_id': 'mytype', 'unit_key': {'name': 'foo'}}
        ]

    @mock.patch.object(ConsumerScheduleManager, '_validate_consumer')
    def test_validation(self, mock_validate):
        mock_validate.side_effect = MissingResource

        self.assertRaises(MissingResource, self.manager.create_schedule, UNIT_INSTALL_ACTION, 'consumer1',
                          self.units, {}, 'PT1H')

        mock_validate.assert_called_once_with('consumer1')

    @mock.patch.object(ScheduledCall, 'save')
    @mock.patch('pulp.server.managers.consumer.cud.ConsumerManager.get_consumer')
    def test_allows_arbitrary_options(self, mock_get_consumer, mock_save):
        self.manager.create_schedule(UNIT_INSTALL_ACTION, 'consumer1',
                                     self.units, {'arbitrary_option': True}, 'PT1H')

        mock_save.assert_called_once_with()

    @mock.patch('pulp.server.managers.consumer.cud.ConsumerManager.get_consumer')
    def test_validate_schedule(self, mock_get_consumer):
        self.assertRaises(InvalidValue, self.manager.create_schedule, UNIT_INSTALL_ACTION, 'consumer1',
                          self.units, {}, 'not a valid schedule')

    @mock.patch('pulp.server.managers.consumer.cud.ConsumerManager.get_consumer')
    def test_validate_units(self, mock_get_consumer):
        self.assertRaises(MissingResource, self.manager.create_schedule, UNIT_INSTALL_ACTION, 'consumer1',
                          [], {}, 'PT1M')


    @mock.patch.object(ScheduledCall, 'save')
    @mock.patch('pulp.server.managers.consumer.cud.ConsumerManager.get_consumer')
    def test_save(self, mock_get_consumer, mock_save):
        iso_schedule = 'PT1H'
        result = self.manager.create_schedule(UNIT_INSTALL_ACTION, 'consumer1',
                                              self.units, {}, iso_schedule, 4, False)

        self.assertEqual(result.iso_schedule, iso_schedule)
        self.assertEqual(result.args, ['consumer1'])
        self.assertEqual(result.kwargs['units'], self.units)
        self.assertEqual(result.kwargs['options'], {})
        self.assertEqual(result.resource, Consumer.build_resource_tag('consumer1'))
        self.assertTrue(result.enabled is False)

        mock_save.assert_called_once_with()


class TestUpdate(unittest.TestCase):
    def setUp(self):
        super(TestUpdate, self).setUp()
        self.manager = ConsumerScheduleManager()
        self.units = [
            {'type_id': 'mytype', 'unit_key': {'name': 'foo'}}
        ]

    @mock.patch.object(ConsumerScheduleManager, '_validate_consumer')
    def test_validation(self, mock_validate):
        mock_validate.side_effect = MissingResource

        self.assertRaises(MissingResource, self.manager.update_schedule, 'consumer1', 'schedule1',
                          self.units)

        mock_validate.assert_called_once_with('consumer1')

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.consumer.cud.ConsumerManager.get_consumer')
    def test_units(self, mock_get_consumer, mock_update):
        result = self.manager.update_schedule('consumer1', 'schedule1', self.units)

        mock_update.assert_called_once_with('schedule1', {'kwargs': {'units': self.units}})

        self.assertEqual(result, mock_update.return_value)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.consumer.cud.ConsumerManager.get_consumer')
    def test_options(self, mock_get_consumer, mock_update):
        options = {'foo': 'bar'}
        result = self.manager.update_schedule('consumer1', 'schedule1', options=options)

        mock_update.assert_called_once_with('schedule1', {'kwargs': {'options': options}})

        self.assertEqual(result, mock_update.return_value)

    @mock.patch('pulp.server.managers.schedule.utils.update')
    @mock.patch('pulp.server.managers.consumer.cud.ConsumerManager.get_consumer')
    def test_other_data(self, mock_get_consumer, mock_update):
        schedule_data = {'enabled': False}
        result = self.manager.update_schedule('consumer1', 'schedule1', schedule_data=schedule_data)

        mock_update.assert_called_once_with('schedule1', {'enabled': False})

        self.assertEqual(result, mock_update.return_value)


class TestDelete(unittest.TestCase):
    def setUp(self):
        super(TestDelete, self).setUp()
        self.manager = ConsumerScheduleManager()

    @mock.patch.object(ConsumerScheduleManager, '_validate_consumer')
    def test_validation(self, mock_validate):
        mock_validate.side_effect = MissingResource

        self.assertRaises(MissingResource, self.manager.delete_schedule, 'consumer1', 'schedule1')

        mock_validate.assert_called_once_with('consumer1')

    @mock.patch('pulp.server.managers.schedule.utils.delete')
    @mock.patch.object(ConsumerScheduleManager, '_validate_consumer')
    def test_calls_delete(self, mock_validate, mock_delete):
        self.manager.delete_schedule('consumer1', 'schedule1')

        mock_delete.assert_called_once_with('schedule1')
        mock_validate.assert_called_once_with('consumer1')
