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
import mock_agent

import pulp.plugins.loader as plugin_loader
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.server.db.model.repository import Repo, RepoDistributor
import pulp.server.managers.factory as factory

# -- test cases ---------------------------------------------------------------

class AgentManagerTests(base.PulpServerTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'test-distributor'

    def setUp(self):
        base.PulpServerTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_loader._create_loader()
        mock_plugins.install()
        mock_agent.install()

    def tearDown(self):
        base.PulpServerTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        config = {'key1' : 'value1', 'key2' : None}
        manager = factory.repo_manager()
        repo = manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            'mock-distributor',
            config,
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)

    def test_unregistered(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_agent_manager()
        manager.unregistered(self.CONSUMER_ID)
        # verify
        # TODO: verify

    def test_bind(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        bind = manager.bind(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID)
        # Test
        manager = factory.consumer_agent_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID)
        # verify
        # TODO: verify

    def test_unbind(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        bind = manager.bind(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID)
        # Test
        manager = factory.consumer_agent_manager()
        manager.unbind(self.CONSUMER_ID, self.REPO_ID)
        # verify
        # TODO: verify

    def test_content_install(self):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='python-gofer', version='0.66')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        manager = factory.consumer_agent_manager()
        manager.install_content(self.CONSUMER_ID, units, options)
        # verify
        # TODO: verify

    def test_content_update(self):
        # Setup
        self.populate()
        # Test
        unit = dict(type_id='rpm', unit_key=dict(name='zsh'))
        units = [unit,]
        options = {}
        manager = factory.consumer_agent_manager()
        manager.update_content(self.CONSUMER_ID, units, options)
        # verify
        # TODO: verify

    def test_content_uninstall(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_agent_manager()
        unit = dict(type_id='rpm', unit_key=dict(name='zsh'))
        units = [unit,]
        options = {}
        manager.uninstall_content(self.CONSUMER_ID, units, options)
        # verify
        # TODO: verify
