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

# Python
import sys
import os

import base
import mock_agent
from pulp.server.agent.hub.pulpagent import PulpAgent as RestAgent
from pulp.server.agent.direct.pulpagent import PulpAgent as DirectAgent


REPOID = 'TEST-REPO'
CONSUMER = {
    'id':'gc',
    'certificate':'XXX',
}
UNIT = {
    'type_id':'rpm',
    'unit_key':{
        'name':'zsh',
    }
}
UNITS = [UNIT,]
OPTIONS = {
    'importkeys':True,
}

TASKID = 'TASK-123'
AGENT_CLASSES = (DirectAgent, RestAgent)


class TestRestAgent(base.PulpServerTests):
    
    def setUp(self):
        base.PulpServerTests.setUp(self)
        mock_agent.install()
    
    def test_unregistered(self):
        for Agent in AGENT_CLASSES:
            # Test
            agent = Agent(CONSUMER)
            agent.consumer.unregistered()
            # Verify
            # TODO:
        
    def test_bind(self):
        # Test
        for Agent in AGENT_CLASSES:
            agent = Agent(CONSUMER)
            print agent.consumer.bind(REPOID)
            # Verify
            # TODO:
        
    def test_unbind(self):
        # Test
        for Agent in AGENT_CLASSES:
            agent = Agent(CONSUMER)
            print agent.consumer.unbind(REPOID)
            # Verify
            # TODO:
        
    def test_install_content(self):
        # Test
        for Agent in AGENT_CLASSES:
            agent = Agent(CONSUMER)
            report = agent.content.install(UNITS, OPTIONS)
            self.validate_succeeded(report)
            print report
        
    def test_update_content(self):
        # Test
        for Agent in AGENT_CLASSES:
            agent = Agent(CONSUMER)
            report = agent.content.update(UNITS, OPTIONS)
            self.validate_succeeded(report)
            print report
        
    def test_uninstall_content(self):
        # Test
        for Agent in AGENT_CLASSES:
            agent = Agent(CONSUMER)
            report = agent.content.uninstall(UNITS, OPTIONS)
            self.validate_succeeded(report)
            print report

    def test_profile_send(self):
        # Test
        for Agent in AGENT_CLASSES:
            agent = Agent(CONSUMER)
            print agent.profile.send()
            # Verify
            # TODO:

    def test_status(self):
        # Test
        for Agent in AGENT_CLASSES:
            print Agent.status(['A','B'])
            # Verify
            # TODO:
            
    def validate_succeeded(self, report):
        # The (direct) implementation returns literal mock method
        # return values (even for asynchronous RMI).
        # The (hub)
        # return (httpcode, mock_return)
        if isinstance(report, tuple):
            # hub
            report = report[1]
        self.assertTrue(report['status'])
        self.assertTrue('reboot' in report)
        details = report['details']
        self.assertEqual(details['units'], UNITS)
        self.assertEqual(details['options'], OPTIONS)
        