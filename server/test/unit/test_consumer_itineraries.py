# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from base import PulpItineraryTests
from pulp.devel import mock_plugins
from pulp.devel import mock_agent
from pulp.server.managers import factory
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.db.model.consumer import Consumer
from pulp.server.itineraries.consumer import *
from pulp.agent.lib.report import DispatchReport


class TestContent(PulpItineraryTests):

    CONSUMER_ID = 'test-consumer'

    def setUp(self):
        PulpItineraryTests.setUp(self)
        Consumer.get_collection().remove()
        mock_plugins.install()
        mock_agent.install()

    def tearDown(self):
        PulpItineraryTests.tearDown(self)
        Consumer.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)

    def test_install(self):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        itinerary = consumer_content_install_itinerary(self.CONSUMER_ID, units, options)
        call_report = self.coordinator.execute_call_asynchronously(itinerary[0])

        # Verify
        self.assertEqual(len(itinerary), 1)
        self.assertTrue('options' in itinerary[0].kwarg_blacklist)
        self.assertNotEqual(call_report.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual install)
        self.run_next()

        # verify agent called
        mock_agent.Content.install.assert_called_with(units, options)

        # simulated asynchronous task result
        report = DispatchReport()
        report.details = {'A':1}
        self.coordinator.complete_call_success(call_report.call_request_id, report.dict())

        # verify result
        call_report = self.coordinator.find_call_reports(call_request_id=call_report.call_request_id)[0]
        self.assertEqual(call_report.state, dispatch_constants.CALL_FINISHED_STATE)
        self.assertTrue(call_report.result['succeeded'])
        self.assertEqual(call_report.result['details'], report.details)
        self.assertEqual(call_report.result['reboot'], report.reboot)

    def test_install_cancelled(self):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        itinerary = consumer_content_install_itinerary(self.CONSUMER_ID, units, options)
        call_report = self.coordinator.execute_call_asynchronously(itinerary[0])

        # run the task
        self.run_next()

        # Verify
        self.assertNotEqual(call_report.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # cancel the task
        self.cancel(call_report.call_request_id)

        # verify agent called
        mock_agent.Admin.cancel.assert_called_with(criteria={'eq': call_report.call_request_id})

    def test_update(self):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        itinerary = consumer_content_update_itinerary(self.CONSUMER_ID, units, options)
        call_report = self.coordinator.execute_call_asynchronously(itinerary[0])

        # Verify
        self.assertEqual(len(itinerary), 1)
        self.assertTrue('options' in itinerary[0].kwarg_blacklist)
        self.assertNotEqual(call_report.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual update)
        self.run_next()

        # verify agent called
        mock_agent.Content.update.assert_called_with(units, options)

        # simulated asynchronous task result
        report = DispatchReport()
        report.details = {'A':1}
        self.coordinator.complete_call_success(call_report.call_request_id, report.dict())

        # verify result
        call_report = self.coordinator.find_call_reports(call_request_id=call_report.call_request_id)[0]
        self.assertEqual(call_report.state, dispatch_constants.CALL_FINISHED_STATE)
        self.assertTrue(call_report.result['succeeded'])
        self.assertEqual(call_report.result['details'], report.details)
        self.assertEqual(call_report.result['reboot'], report.reboot)

    def test_update_cancelled(self):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        itinerary = consumer_content_update_itinerary(self.CONSUMER_ID, units, options)
        call_report = self.coordinator.execute_call_asynchronously(itinerary[0])

        # run the task
        self.run_next()

        # Verify
        self.assertNotEqual(call_report.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # cancel the task
        self.cancel(call_report.call_request_id)

        # verify agent called
        mock_agent.Admin.cancel.assert_called_with(criteria={'eq': call_report.call_request_id})

    def test_uninstall(self):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        itinerary = consumer_content_uninstall_itinerary(self.CONSUMER_ID, units, options)
        call_report = self.coordinator.execute_call_asynchronously(itinerary[0])

        # Verify
        self.assertEqual(len(itinerary), 1)
        self.assertTrue('options' in itinerary[0].kwarg_blacklist)
        self.assertNotEqual(call_report.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1 (actual uninstall)
        self.run_next()

        # verify agent called
        mock_agent.Content.uninstall.assert_called_with(units, options)

        # simulated asynchronous task result
        report = DispatchReport()
        report.details = {'A':1}
        self.coordinator.complete_call_success(call_report.call_request_id, report.dict())

        # verify result
        call_report = self.coordinator.find_call_reports(call_request_id=call_report.call_request_id)[0]
        self.assertEqual(call_report.state, dispatch_constants.CALL_FINISHED_STATE)
        self.assertTrue(call_report.result['succeeded'])
        self.assertEqual(call_report.result['details'], report.details)
        self.assertEqual(call_report.result['reboot'], report.reboot)

    def test_uninstall_cancelled(self):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        itinerary = consumer_content_uninstall_itinerary(self.CONSUMER_ID, units, options)
        call_report = self.coordinator.execute_call_asynchronously(itinerary[0])

        # run the task
        self.run_next()

        # Verify
        self.assertNotEqual(call_report.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # cancel the task
        self.cancel(call_report.call_request_id)

        # verify agent called
        mock_agent.Admin.cancel.assert_called_with(criteria={'eq': call_report.call_request_id})