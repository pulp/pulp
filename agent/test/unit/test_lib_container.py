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

from mock import Mock
from pprint import pprint
from pulp.agent.lib.container import *
from pulp.agent.lib.dispatcher import *
from pulp.agent.lib.conduit import Conduit
from pulp.common.config import PropertyNotFound, SectionNotFound
from pulp.devel.mock_handlers import MockDeployer


class TestConduit(Conduit):

    class Test:
        def __init__(self):
            self.succeeded = True
            self.exception = None

    def __init__(self):
        self.test = self.Test()


class TestHandlerContainer(unittest.TestCase):

    def setUp(self):
        self.deployer = MockDeployer()
        self.deployer.deploy()

    def tearDown(self):
        self.deployer.clean()

    def container(self):
        return Container(MockDeployer.CONF_D, [MockDeployer.PATH])

    def test_loading(self):
        # Setup
        container = self.container()
        # Test
        container.load()
        # Verify
        handler = container.find('rpm')
        self.assertTrue(handler is not None)
        handler = container.find('srpm')
        self.assertTrue(handler is not None)
        handler = container.find('puppet')
        self.assertTrue(handler is None)
        handler = container.find('yum', BIND)
        self.assertTrue(handler is not None)
        handler = container.find('Linux', SYSTEM)
        self.assertTrue(handler is not None)
        errors = container.errors()
        self.assertEquals(len(errors), 3)
        self.assertTrue(isinstance(errors[0], ImportError))
        self.assertTrue(isinstance(errors[1], PropertyNotFound))
        self.assertTrue(isinstance(errors[2], SectionNotFound))

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
        return Container(MockDeployer.CONF_D, [MockDeployer.PATH])

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
        self.assertTrue(report.succeeded)
        self.assertEquals(report.num_changes, 2)
        self.assertFalse(report.reboot['scheduled'])

    def test_install_failed(self):
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
        handler = dispatcher.container.find('rpm')
        report = ContentReport()
        report.set_failed({'a':1})
        handler.install = Mock(return_value=report)
        # Test
        options = {}
        conduit = Conduit()
        report = dispatcher.install(conduit, units, options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 0)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(report.details['rpm']['succeeded'])
        self.assertEqual(report.details['rpm']['details'], {'a':1})

    def test_install_raised(self):
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
        handler = dispatcher.container.find('rpm')
        handler.install = Mock(side_effect=ValueError())
        # Test
        options = {}
        conduit = Conduit()
        report = dispatcher.install(conduit, units, options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 0)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(report.details['rpm']['succeeded'])
        self.assertTrue(report.details['rpm']['details'].has_key('message'))
        self.assertTrue(report.details['rpm']['details'].has_key('trace'))

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
        self.assertTrue(report.succeeded)
        self.assertEquals(report.num_changes, 2)
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
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 1)
        # RPM passed
        rpm = report.details['rpm']
        self.assertTrue(rpm['succeeded'])
        # XXX failed
        xxx = report.details['xxx']
        self.assertFalse(xxx['succeeded'])

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
        self.assertTrue(report.succeeded)
        self.assertEquals(report.num_changes, 2)

    def test_update_failed(self):
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
        handler = dispatcher.container.find('rpm')
        report = ContentReport()
        report.set_failed({'a':1})
        handler.update = Mock(return_value=report)
        # Test
        options = {}
        conduit = Conduit()
        report = dispatcher.update(conduit, units, options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 0)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(report.details['rpm']['succeeded'])
        self.assertEqual(report.details['rpm']['details'], {'a':1})

    def test_update_raised(self):
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
        handler = dispatcher.container.find('rpm')
        handler.update = Mock(side_effect=ValueError())
        # Test
        options = {}
        conduit = Conduit()
        report = dispatcher.update(conduit, units, options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 0)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(report.details['rpm']['succeeded'])
        self.assertTrue(report.details['rpm']['details'].has_key('message'))
        self.assertTrue(report.details['rpm']['details'].has_key('trace'))

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
        self.assertTrue(report.succeeded)
        self.assertEquals(report.num_changes, 1)

    def test_uninstall_failed(self):
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
        handler = dispatcher.container.find('rpm')
        report = ContentReport()
        report.set_failed({'a':1})
        handler.uninstall = Mock(return_value=report)
        # Test
        options = {}
        conduit = Conduit()
        report = dispatcher.uninstall(conduit, units, options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 0)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(report.details['rpm']['succeeded'])
        self.assertEqual(report.details['rpm']['details'], {'a':1})

    def test_uninstall_raised(self):
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
        handler = dispatcher.container.find('rpm')
        handler.uninstall = Mock(side_effect=ValueError())
        # Test
        options = {}
        conduit = Conduit()
        report = dispatcher.uninstall(conduit, units, options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 0)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(report.details['rpm']['succeeded'])
        self.assertTrue(report.details['rpm']['details'].has_key('message'))
        self.assertTrue(report.details['rpm']['details'].has_key('trace'))

    def test_profile(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        report = dispatcher.profile(conduit)
        pprint(report.dict())
        self.assertTrue(report.succeeded)
        self.assertEquals(report.num_changes, 0)

    def test_profile_failed(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        handler = dispatcher.container.find('rpm')
        report = ProfileReport()
        report.set_failed({'a':1})
        handler.profile = Mock(return_value=report)
        # Test
        conduit = Conduit()
        report = dispatcher.profile(conduit)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 0)
        self.assertFalse(report.details['rpm']['succeeded'])
        self.assertEqual(report.details['rpm']['details'], {'a':1})

    def test_profile_raised(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        handler = dispatcher.container.find('rpm')
        handler.profile = Mock(side_effect=ValueError())
        # Test
        conduit = Conduit()
        report = dispatcher.profile(conduit)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 0)
        self.assertFalse(report.details['rpm']['succeeded'])
        self.assertTrue(report.details['rpm']['details'].has_key('message'))
        self.assertTrue(report.details['rpm']['details'].has_key('trace'))

    def test_reboot(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        report = dispatcher.reboot(conduit, {})
        pprint(report.dict())
        self.assertTrue(report.succeeded)
        self.assertEquals(report.num_changes, 0)

    def test_bind(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id, details={})
        options = {}
        report = dispatcher.bind(conduit, [binding,], options)
        pprint(report.dict())
        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 1)
        details = report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertTrue(details['succeeded'])
        self.assertEqual(details['details'], {})

    def test_bind_failed(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        dispatcher = Dispatcher(self.container())
        handler = dispatcher.container.find(type_id, BIND)
        report = BindReport(repo_id)
        report.set_failed({'a':1})
        handler.bind = Mock(return_value=report)
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id, details={})
        options = {}
        report = dispatcher.bind(conduit, [binding,], options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEqual(report.num_changes, 0)
        details = report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertFalse(details['succeeded'])
        self.assertEqual(details['details'], {'a':1})

    def test_bind_raised(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        dispatcher = Dispatcher(self.container())
        handler = dispatcher.container.find(type_id, BIND)
        handler.bind = Mock(side_effect=ValueError())
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id, details={})
        options = {}
        report = dispatcher.bind(conduit, [binding,], options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEqual(report.num_changes, 0)
        details = report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertTrue(details['details'].has_key('message'))
        self.assertTrue(details['details'].has_key('trace'))

    def test_unbind(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id)
        options = {}
        report = dispatcher.unbind(conduit, [binding,], options)
        pprint(report.dict())
        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 1)
        details = report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertEqual(details['details'], {})

    def test_unbind_failed(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        dispatcher = Dispatcher(self.container())
        handler = dispatcher.container.find(type_id, BIND)
        report = BindReport(repo_id)
        report.set_failed({'a':1})
        handler.unbind = Mock(return_value=report)
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id)
        options = {}
        report = dispatcher.unbind(conduit, [binding,], options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEqual(report.num_changes, 0)
        details = report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertFalse(details['succeeded'])
        self.assertEqual(details['details'], {'a':1})

    def test_unbind_raised(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        dispatcher = Dispatcher(self.container())
        handler = dispatcher.container.find(type_id, BIND)
        handler.unbind = Mock(side_effect=ValueError)
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id)
        options = {}
        report = dispatcher.unbind(conduit, [binding,], options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEqual(report.num_changes, 0)
        details = report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertFalse(details['succeeded'])
        self.assertTrue(details['details'].has_key('message'))
        self.assertTrue(details['details'].has_key('trace'))

    def test_unbind_all(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        binding = dict(type_id=None, repo_id=repo_id)
        options = {}
        report = dispatcher.unbind(conduit, [binding,], options)
        pprint(report.dict())
        self.assertTrue(report.succeeded)
        self.assertEqual(report.num_changes, 1)
        details = report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertEqual(details['details'], {})

    def test_unbind_all_failed(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        dispatcher = Dispatcher(self.container())
        handler = dispatcher.container.find(type_id, BIND)
        report = BindReport(repo_id)
        report.set_failed({'a':1})
        handler.unbind = Mock(return_value=report)
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id)
        options = {}
        report = dispatcher.unbind(conduit, [binding,], options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEqual(report.num_changes, 0)
        details = report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertFalse(details['succeeded'])
        self.assertEqual(details['details'], {'a':1})

    def test_unbind_all_raised(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        dispatcher = Dispatcher(self.container())
        handler = dispatcher.container.find(type_id, BIND)
        handler.unbind = Mock(side_effect=ValueError)
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id)
        options = {}
        report = dispatcher.unbind(conduit, [binding,], options)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEqual(report.num_changes, 0)
        details = report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertFalse(details['succeeded'])
        self.assertTrue(details['details'].has_key('message'))
        self.assertTrue(details['details'].has_key('trace'))

    def test_clean(self):
        type_id = 'yum'
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        conduit = Conduit()
        report = dispatcher.clean(conduit)
        pprint(report.dict())
        self.assertTrue(report.succeeded)
        self.assertEquals(report.num_changes, 1)
        details = report.details[type_id]
        self.assertEqual(details['details'], {})

    def test_clean_failed(self):
        type_id = 'yum'
        # Setup
        dispatcher = Dispatcher(self.container())
        handler = dispatcher.container.find(type_id, BIND)
        report = CleanReport()
        report.set_failed({'a':1})
        handler.clean = Mock(return_value=report)
        # Test
        conduit = Conduit()
        report = dispatcher.clean(conduit)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 0)
        details = report.details[type_id]
        self.assertEqual(details['details'], {'a':1})

    def test_clean_raised(self):
        type_id = 'yum'
        # Setup
        dispatcher = Dispatcher(self.container())
        handler = dispatcher.container.find(type_id, BIND)
        handler.clean = Mock(side_effect=ValueError)
        # Test
        conduit = Conduit()
        report = dispatcher.clean(conduit)
        pprint(report.dict())
        self.assertFalse(report.succeeded)
        self.assertEquals(report.num_changes, 0)
        details = report.details[type_id]
        self.assertTrue(details['details'].has_key('message'))
        self.assertTrue(details['details'].has_key('trace'))
