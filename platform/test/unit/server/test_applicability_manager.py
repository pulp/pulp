#!/usr/bin/python
#
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

import base
import mock_plugins

from mock import Mock
from pulp.plugins.loader import api as plugins
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.consumer import Consumer, UnitProfile
from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.plugins.model import ApplicabilityReport
from pulp.server.managers import factory as factory
from pulp.server.exceptions import PulpExecutionException

# -- test cases ---------------------------------------------------------------

class ApplicabilityManagerTests(base.PulpServerTests):

    CONSUMER_IDS = ['test-1', 'test-2']
    FILTER = {'id':{'$in':CONSUMER_IDS}}
    SORT = [{'id':1}]
    CRITERIA = Criteria(filters=FILTER, sort=SORT)
    PROFILE = [1,2,3]

    def setUp(self):
        base.PulpServerTests.setUp(self)
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        plugins._create_manager()
        mock_plugins.install()
        profiler = plugins.get_profiler_by_type('rpm')[0]
        profiler.unit_applicable = \
            Mock(side_effect=lambda i,u,c,x:
                 ApplicabilityReport(u, True, 'mysummary', 'mydetails'))

    def tearDown(self):
        base.PulpServerTests.tearDown(self)
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        manager = factory.consumer_manager()
        for id in self.CONSUMER_IDS:
            manager.register(id)
        manager = factory.consumer_profile_manager()
        for id in self.CONSUMER_IDS:
            manager.create(id, 'rpm', self.PROFILE)

    def test_applicability(self):
        # Setup
        self.populate()
        # Test
        units = [
            {'type_id':'rpm', 'unit_key':{'name':'zsh'}},
            {'type_id':'rpm', 'unit_key':{'name':'ksh'}},
            {'type_id':'mock-type', 'unit_key':{'name':'abc'}},
            {'type_id':'mock-type', 'unit_key':{'name':'def'}}
        ]
        manager = factory.consumer_applicability_manager()
        applicability = manager.units_applicable(self.CRITERIA, units)
        # verify
        self.assertEquals(len(applicability), 2)
        for id in self.CONSUMER_IDS:
            for report in applicability[id]:
                if report.unit in units[1:2]:
                    self.assertTrue(report.applicable)
                    self.assertEquals(report.summary, 'mysummary')
                    self.assertEquals(report.details, 'mydetails')
                    continue
                if report.unit in units[2:3]:
                    self.assertFalse(report.applicable)
                    self.assertEquals(report.summary, 'mocked')
                    self.assertEquals(report.details, None)
                    continue
        profiler, cfg = plugins.get_profiler_by_type('rpm')
        call = 0
        args = [c[0] for c in profiler.unit_applicable.call_args_list]
        for id in self.CONSUMER_IDS:
            for unit in units[0:2]:
                self.assertEquals(args[call][0].id, id)
                self.assertEquals(args[call][0].profiles, {'rpm':self.PROFILE})
                self.assertEquals(args[call][1], unit)
                self.assertEquals(args[call][2], cfg)
                self.assertEquals(args[call][3].__class__, ProfilerConduit)
                call += 1

    def test_profiler_exception(self):
        # Setup
        self.populate()
        profiler, cfg = plugins.get_profiler_by_type('rpm')
        profiler.unit_applicable = Mock(side_effect=KeyError)
        # Test
        units = [
            {'type_id':'rpm', 'unit_key':{'name':'zsh'}},
            {'type_id':'rpm', 'unit_key':{'name':'ksh'}},
            {'type_id':'mock-type', 'unit_key':{'name':'abc'}},
            {'type_id':'mock-type', 'unit_key':{'name':'def'}}
        ]
        manager = factory.consumer_applicability_manager()
        self.assertRaises(
            PulpExecutionException,
            manager.units_applicable,
            self.CRITERIA,
            units)

    def test_profiler_notfound(self):
        # Setup
        self.populate()
        # Test
        units = [
            {'type_id':'rpm', 'unit_key':{'name':'zsh'}},
            {'type_id':'xxx', 'unit_key':{'name':'abc'}}
        ]
        manager = factory.consumer_applicability_manager()
        self.assertRaises(
            PulpExecutionException,
            manager.units_applicable,
            self.CRITERIA,
            units)
