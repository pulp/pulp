#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import unittest

from pprint import pprint
from mock_handlers import MockDeployer
from pulp.agent.lib.container import *
from pulp.agent.lib.dispatcher import *
from pulp.agent.lib.conduit import Conduit
from pulp.common.config import PropertyNotFound, SectionNotFound


class TestHandlerContainer(unittest.TestCase):

    def setUp(self):
        self.deployer = MockDeployer()
        self.deployer.deploy()

    def tearDown(self):
        self.deployer.clean()
        
    def container(self):
        return Container(MockDeployer.ROOT, MockDeployer.PATH)

    def test_loading(self):
        # Setup
        container = self.container()
        # Test
        container.load()
        # Verify
        handler = container.find('rpm')
        self.assertTrue(handler is not None)
        handler = container.find('puppet')
        self.assertTrue(handler is None)
        errors = container.errors()
        self.assertEquals(len(errors), 2)
        self.assertTrue(isinstance(errors[0], PropertyNotFound))
        self.assertTrue(isinstance(errors[1], SectionNotFound))

    def test_find(self):
        # Setup
        container = self.container()
        # Test
        container.load()
        handler = container.find('xxx')
        # Verify
        self.assertTrue(handler is None)


class TestDispatcher(unittest.TestCase):

    def setUp(self):
        self.deployer = MockDeployer()
        self.deployer.deploy()

    def tearDown(self):
        self.deployer.clean()

    def container(self):
        return Container(MockDeployer.ROOT, MockDeployer.PATH)

    def test_install(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='ksh'))
        units.append(unit)
        options = {}
        # Test
        conduit = Conduit()
        report = dispatcher.install(conduit, units, options)
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 2)
        self.assertFalse(report.reboot['scheduled'])

    def test_install_reboot(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        options = dict(reboot=True)
        # Test
        conduit = Conduit()
        report = dispatcher.install(conduit, [unit], options)
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 2)
        self.assertTrue(report.reboot['scheduled'])

    def test_install_failed_no_handler(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='xxx',
            unit_key=dict(name='ksh'))
        units.append(unit)
        options = {}
        # Test
        conduit = Conduit()
        report = dispatcher.install(conduit, units, options)
        pprint(report.dict())
        self.assertFalse(report.status)
        self.assertEquals(report.chgcnt, 1)
        # RPM passed
        rpm = report.details['rpm']
        self.assertTrue(rpm['status'])
        # XXX failed
        xxx = report.details['xxx']
        self.assertFalse(xxx['status'])

    def test_update(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='ksh'))
        units.append(unit)
        options = {}
        # Test
        conduit = Conduit()
        report = dispatcher.update(conduit, units, options)
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 2)

    def test_uninstall(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        options = {}
        # Test
        conduit = Conduit()
        report = dispatcher.uninstall(conduit, [unit], options)
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)

    def test_profile(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        report = dispatcher.profile(conduit)
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 0)

    def test_reboot(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        report = dispatcher.reboot(conduit, {})
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 0)

    def test_bind(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        definition = dict(type_id='yum', repo={})
        report = dispatcher.bind(conduit, [definition,])
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)

    def test_rebind(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        definition = dict(type_id='yum', repo={})
        report = dispatcher.rebind(conduit, [definition,])
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)

    def test_unbind(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        report = dispatcher.unbind(conduit, 'repo-1')
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)

    def test_clean(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        report = dispatcher.clean(conduit)
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)