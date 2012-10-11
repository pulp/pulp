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


REPO_ID = 'repo_1'
REPOSITORY = {'id':REPO_ID}
DETAILS = {}
DEFINITIONS = [
    {'type_id':'yum',
     'repository':REPOSITORY,
     'details':DETAILS,}
]
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
    'xxx':True,
}

TASKID = 'TASK-123'


class TestAgent(base.PulpServerTests):
    
    def setUp(self):
        base.PulpServerTests.setUp(self)
        mock_agent.install()
        mock_agent.reset()
    
    def test_unregistered(self):
        # Test
        agent = DirectAgent(CONSUMER)
        agent.consumer.unregistered()
        # Verify
        mock_agent.Consumer.unregistered.assert_called_once_with()
        
    def test_bind(self):
        # Test
        agent = DirectAgent(CONSUMER)
        result = agent.consumer.bind(DEFINITIONS, OPTIONS)
        # Verify
        mock_agent.Consumer.bind.assert_called_once_with(DEFINITIONS, OPTIONS)

    def test_rebind(self):
        # Test
        agent = DirectAgent(CONSUMER)
        result = agent.consumer.rebind(DEFINITIONS, OPTIONS)
        # Verify
        mock_agent.Consumer.rebind.assert_called_once_with(DEFINITIONS, OPTIONS)
        
    def test_unbind(self):
        # Test
        agent = DirectAgent(CONSUMER)
        result = agent.consumer.unbind(REPO_ID)
        # Verify
        mock_agent.Consumer.unbind.assert_called_once_with(REPO_ID)
        
    def test_install_content(self):
        # Test
        agent = DirectAgent(CONSUMER)
        result = agent.content.install(UNITS, OPTIONS)
        # Verify
        mock_agent.Content.install.assert_called_once_with(UNITS, OPTIONS)
        
    def test_update_content(self):
        # Test
        agent = DirectAgent(CONSUMER)
        result = agent.content.update(UNITS, OPTIONS)
        # Verify
        mock_agent.Content.update.assert_called_once_with(UNITS, OPTIONS)
        
    def test_uninstall_content(self):
        # Test
        agent = DirectAgent(CONSUMER)
        result = agent.content.uninstall(UNITS, OPTIONS)
        # Verify
        mock_agent.Content.uninstall.assert_called_once_with(UNITS, OPTIONS)

    def test_profile_send(self):
        # Test
        agent = DirectAgent(CONSUMER)
        print agent.profile.send()
        # Verify
        mock_agent.Profile.send.assert_called_once_with()

    def test_status(self):
        # Test
        print RestAgent.status(['A','B'])
        # Verify
        # TODO: verify


class TestRestAgent(base.PulpServerTests):

    def setUp(self):
        base.PulpServerTests.setUp(self)
        mock_agent.install()
        mock_agent.reset()

    def test_unregistered(self):
        # Test
        agent = RestAgent(CONSUMER)
        agent.consumer.unregistered()
        # Verify
        mock_agent.Consumer.unregistered.assert_called_once_with()

    def test_bind(self):
        # Test
        agent = RestAgent(CONSUMER)
        result = agent.consumer.bind(DEFINITIONS, OPTIONS)
        # Verify
        mock_agent.Consumer.bind.assert_called_once_with(DEFINITIONS, OPTIONS)

    def test_rebind(self):
        # Test
        agent = RestAgent(CONSUMER)
        result = agent.consumer.rebind(DEFINITIONS, OPTIONS)
        # Verify
        mock_agent.Consumer.rebind.assert_called_once_with(DEFINITIONS, OPTIONS)

    def test_unbind(self):
        # Test
        agent = RestAgent(CONSUMER)
        result = agent.consumer.unbind(REPO_ID)
        # Verify
        mock_agent.Consumer.unbind.assert_called_once_with(REPO_ID)

    def test_install_content(self):
        # Test
        agent = RestAgent(CONSUMER)
        result = agent.content.install(UNITS, OPTIONS)
        # Verify
        mock_agent.Content.install.assert_called_once_with(UNITS, OPTIONS)

    def test_update_content(self):
        # Test
        agent = RestAgent(CONSUMER)
        result = agent.content.update(UNITS, OPTIONS)
        # Verify
        mock_agent.Content.update.assert_called_once_with(UNITS, OPTIONS)

    def test_uninstall_content(self):
        # Test
        agent = RestAgent(CONSUMER)
        result = agent.content.uninstall(UNITS, OPTIONS)
        # Verify
        mock_agent.Content.uninstall.assert_called_once_with(UNITS, OPTIONS)

    def test_profile_send(self):
        # Test
        agent = RestAgent(CONSUMER)
        print agent.profile.send()
        # Verify
        mock_agent.Profile.send.assert_called_once_with()

    def test_status(self):
        # Test
        print RestAgent.status(['A','B'])
        # Verify
        # TODO: verify