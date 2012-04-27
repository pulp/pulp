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

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil
import mockagent
from pulp.server.gc_agent.hub.pulpagent import PulpAgent as RestAgent
from pulp.server.gc_agent.direct.pulpagent import PulpAgent as DirectAgent


REPOID = 'TEST-REPO'
CONSUMER = {
    'id':'gc',
    'certificate':'XXX',
}
UNIT = {
    'type_id':'rpm',
    'metadata':{
        'name':'zsh',
    }
}
UNITS = [UNIT,]
OPTIONS = {
    'importkeys':True,
}

TASKID = 'TASK-123'
AGENT_CLASSES = (DirectAgent, RestAgent)


class TestRestAgent(testutil.PulpTest):
    
    def setUp(self):
        testutil.PulpTest.setUp(self)
        mockagent.install()
    
    def test_unregistered(self):
        for Agent in AGENT_CLASSES:
            # Test
            agent = Agent(CONSUMER)
            print agent.consumer.unregistered()
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
            print agent.content.install(UNITS, OPTIONS)
            # Verify
            # TODO:
        
    def test_update_content(self):
        # Test
        for Agent in AGENT_CLASSES:
            agent = Agent(CONSUMER)
            print agent.content.update(UNITS, OPTIONS)
            # Verify
            # TODO:
        
    def test_uninstall_content(self):
        # Test
        for Agent in AGENT_CLASSES:
            agent = Agent(CONSUMER)
            print agent.content.uninstall(UNITS, OPTIONS)
            # Verify
            # TODO:

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