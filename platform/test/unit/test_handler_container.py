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
        handler = container.find('rpm')
        # Verify
        self.assertTrue(handler is not None)
        
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
        report = dispatcher.install(units, options)
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
        report = dispatcher.install([unit], options)
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)
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
        report = dispatcher.install(units, options)
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
        report = dispatcher.update(units, options)
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
        report = dispatcher.uninstall([unit], options)
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)

    def test_profile(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        report = dispatcher.profile()
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 0)

    def test_reboot(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        report = dispatcher.reboot()
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 0)

    def test_bind(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        definition = dict(type_id='yum', repo={})
        report = dispatcher.bind([definition,])
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)

    def test_rebind(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        definition = dict(type_id='yum', repo={})
        report = dispatcher.rebind([definition,])
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)

    def test_unbind(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        report = dispatcher.unbind('repo-1')
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)

    def test_clean(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        report = dispatcher.clean()
        pprint(report.dict())
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 1)