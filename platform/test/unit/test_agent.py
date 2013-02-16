# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from iniparse import INIConfig
from logging import root
import unittest

import mock


TEST_CN = 'test_cn'
TEST_CONFIG = INIConfig()


class MockPlugin(object):

    def cfg(self):
        conf = INIConfig()
        conf.heartbeat.seconds = 0
        conf.rest.host = ''
        conf.rest.port = 0
        conf.rest.clientcert = ''
        return conf


class MockProgress(object):

    def __init__(self):
        self.details = None
        self.report = mock.Mock()


class MockContext(object):

    def __init__(self):
        self.progress = MockProgress()

    def current(self):
        return self


class TestConduit(unittest.TestCase):

    @mock.patch('pulp.agent.lib.dispatcher.Dispatcher')
    @mock.patch('gofer.agent.plugin.Plugin.find', return_value=MockPlugin())
    @mock.patch('pulp.common.bundle.Bundle.cn', return_value=TEST_CN)
    @mock.patch('gofer.agent.logutil.getLogger', return_value=root)
    def test_consumer_id(self, *unused):
        from pulp.agent.gofer.pulpplugin import Conduit
        conduit = Conduit()
        consumer_id = conduit.consumer_id
        self.assertEqual(consumer_id, TEST_CN)

    @mock.patch('pulp.agent.lib.dispatcher.Dispatcher')
    @mock.patch('gofer.agent.plugin.Plugin.find', return_value=MockPlugin())
    @mock.patch('pulp.agent.gofer.pulpplugin.Config', return_value=TEST_CONFIG)
    @mock.patch('gofer.agent.logutil.getLogger', return_value=root)
    def test_get_consumer_config(self, *unused):
        # Don't see any value in this test but added for completeness.
        from pulp.agent.gofer.pulpplugin import Conduit
        conduit = Conduit()
        conf = conduit.get_consumer_config()
        self.assertEqual(conf, TEST_CONFIG)

    @mock.patch('pulp.agent.lib.dispatcher.Dispatcher')
    @mock.patch('gofer.agent.plugin.Plugin.find', return_value=MockPlugin())
    @mock.patch('gofer.agent.rmi.Context.current', return_value=MockContext())
    @mock.patch('gofer.agent.logutil.getLogger', return_value=root)
    def test_update_progress(self, mock_get_logger, mock_context, *unused):
        from pulp.agent.gofer.pulpplugin import Conduit
        conduit = Conduit()
        report = {'a': 1}
        conduit.update_progress(report)
        self.assertEqual(report, mock_context.return_value.progress.details)
        self.assertEqual(1, mock_context.return_value.progress.report.call_count)
