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

import os
import sys
import shutil
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pprint import pprint
from mock_handlers import MockInstaller
from pulp.client.consumer.agent.container import *
from pulp.client.consumer.agent.dispatcher import *



class TestHandlerContainer(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)
        self.mock = MockInstaller()
        self.mock.install()


    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        self.mock.clean()
        
    def container(self):
        return Container(MockInstaller.ROOT, MockInstaller.PATH)

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


class TestDispatcher(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)
        self.mock = MockInstaller()
        self.mock.install()


    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        self.mock.clean()

    def container(self):
        return Container(MockInstaller.ROOT, MockInstaller.PATH)

    def test_install(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        options = {}
        # Test
        report = dispatcher.install([unit], options)
        pprint(report.dict())
        # Verify
        # TODO: verify

    def test_update(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        options = {}
        # Test
        report = dispatcher.update([unit], options)
        pprint(report.dict())
        # Verify
        # TODO: verify

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
        # Verify
        # TODO: verify

    def test_profile(self):
        # Setup
        dispatcher = Dispatcher(self.container())
        # Test
        profile = dispatcher.profile('rpm')
        pprint(profile)
        # Verify
        # TODO: verify