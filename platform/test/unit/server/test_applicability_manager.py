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
    CONSUMER_CRITERIA = Criteria(filters=FILTER, sort=SORT)
    REPO_CRITERIA = None
    PROFILE = [{'name':'zsh', 'version':'1.0'}, {'name':'ksh', 'version':'1.0'}]

    def setUp(self):
        base.PulpServerTests.setUp(self)
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()
        plugins._create_manager()
        mock_plugins.install()
        profiler, cfg = plugins.get_profiler_by_type('rpm')
        profiler.units_applicable = \
            Mock(side_effect=lambda i,r,t,u,c,x:
                 [ApplicabilityReport('mysummary', 'mydetails')])

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

    def test_profiler_no_exception(self):
        # Setup
        self.populate()
        profiler, cfg = plugins.get_profiler_by_type('rpm')
        profiler.units_applicable = Mock(side_effect=KeyError)
        # Test
        units = {'rpm': [{'name':'zsh'},
                         {'name':'ksh'}],
                 'mock-type': [{'name':'abc'},
                               {'name':'def'}]
                }
        manager = factory.consumer_applicability_manager()
        result = manager.units_applicable(self.CONSUMER_CRITERIA, self.REPO_CRITERIA, units)
        self.assertTrue('test-1' in result.keys())
        self.assertTrue('test-2' in result.keys())

    def test_no_exception_for_profiler_notfound(self):
        # Setup
        self.populate()
        # Test
        units = {'rpm': [{'name':'zsh'}],
                 'xxx': [{'name':'abc'}]
                }
        manager = factory.consumer_applicability_manager()
        result = manager.units_applicable(self.CONSUMER_CRITERIA, self.REPO_CRITERIA, units)
        self.assertTrue('test-1' in result.keys())
        self.assertTrue('test-2' in result.keys())
