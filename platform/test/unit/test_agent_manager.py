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

from mock import patch
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.profiler import InvalidUnitsRequested
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.exceptions import PulpDataException
from pulp.server.managers import factory
from pulp.server.compat import json, json_util


CONSUMER_PAYLOAD = dict(A=1, B=2, C=3)


# -- test cases ---------------------------------------------------------------

class AgentManagerTests(base.PulpServerTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'mock-distributor'
    REPOSITORY = {'id':REPO_ID}
    DETAILS = {}
    OPTIONS = { 'xxx' : 123 }

    def setUp(self):
        base.PulpServerTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
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
        mock_agent.Consumer.unregistered.assert_called_once_with()

    @patch('pulp.server.managers.repo.distributor.RepoDistributorManager.create_bind_payload',
           return_value=CONSUMER_PAYLOAD)
    def test_bind(self, unused):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        manager = factory.consumer_agent_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID, self.OPTIONS)
        # verify
        manager = factory.repo_query_manager()
        repo = manager.get_repository(self.REPO_ID)
        definitions = [
            dict(type_id=self.DISTRIBUTOR_ID,
                 repository=repo,
                 details=CONSUMER_PAYLOAD)
        ]
        args = mock_agent.Consumer.bind.call_args[0]
        self.assertEquals(json.dumps(args[0], default=json_util.default),
                          json.dumps(definitions, default=json_util.default))
        self.assertEquals(json.dumps(args[1], default=json_util.default),
                          json.dumps(self.OPTIONS, default=json_util.default))
        manager = factory.consumer_bind_manager()
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        requests = bind['consumer_requests']
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]['request_id'], None)
        self.assertEqual(requests[0]['status'], 'pending')

    @patch('pulp.server.managers.repo.distributor.RepoDistributorManager.create_bind_payload',
           return_value=CONSUMER_PAYLOAD)
    def test_rebind(self, unused):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        binding = dict(
            consumer_id=self.CONSUMER_ID,
            repo_id=self.REPO_ID,
            distributor_id=self.DISTRIBUTOR_ID
        )
        manager = factory.consumer_agent_manager()
        manager.rebind(self.CONSUMER_ID, [binding], self.OPTIONS)
        # verify
        manager = factory.repo_query_manager()
        repo = manager.get_repository(self.REPO_ID)
        definitions = [
            dict(type_id=self.DISTRIBUTOR_ID,
                 repository=repo,
                 details=CONSUMER_PAYLOAD)
        ]
        args = mock_agent.Consumer.rebind.call_args[0]
        self.assertEquals(json.dumps(args[0], default=json_util.default),
                          json.dumps(definitions, default=json_util.default))
        self.assertEquals(json.dumps(args[1], default=json_util.default),
                          json.dumps(self.OPTIONS, default=json_util.default))
        manager = factory.consumer_bind_manager()
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        requests = bind['consumer_requests']
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]['request_id'], None)
        self.assertEqual(requests[0]['status'], 'pending')

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
        manager.unbind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID, self.OPTIONS)
        # verify
        mock_agent.Consumer.unbind.assert_called_once_with(self.REPO_ID, self.OPTIONS)
        manager = factory.consumer_bind_manager()
        bind = manager.get_bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        requests = bind['consumer_requests']
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]['request_id'], None)
        self.assertEqual(requests[0]['status'], 'pending')

    def test_content_install(self):
        # Setup
        self.populate()
        # Test
        units = [
            {'type_id':'rpm',
             'unit_key':{'name':'zsh', 'version':'1.0'}},
            {'type_id':'rpm',
             'unit_key':{'name':'bar', 'version':'1.0'}},
            {'type_id':'rpm',
             'unit_key':{'name':'abc', 'version':'1.0'}},
            {'type_id':'mock-type',
             'unit_key':{'name':'monster', 'version':'5.0'}},
            {'type_id':'unsupported',
             'unit_key':{'name':'xxx', 'version':'1.0'}},
        ]
        options = dict(importkeys=True)
        manager = factory.consumer_agent_manager()
        manager.install_content(self.CONSUMER_ID, units, options)
        # Verify
        # agent call
        params = mock_agent.Content.install.call_args[0]
        self.assertEqual(sorted(params[0]), sorted(units))
        self.assertEqual(params[1], options)
        # profiler call
        profiler = plugin_api.get_profiler_by_type('rpm')[0]
        pargs = profiler.install_units.call_args[0]
        self.assertEquals(pargs[0].id, self.CONSUMER_ID)
        self.assertEquals(pargs[0].profiles, {})
        self.assertEquals(pargs[1], units[:3])
        self.assertEquals(pargs[2], options)
        profiler = plugin_api.get_profiler_by_type('mock-type')[0]
        pargs = profiler.install_units.call_args[0]
        self.assertEquals(pargs[0].id, self.CONSUMER_ID)
        self.assertEquals(pargs[0].profiles, {})
        self.assertEquals(pargs[1], units[3:4])
        self.assertEquals(pargs[2], options)

    def test_install_invalid_units(self):
        # Setup
        self.populate()

        invalid_units = [{'type_id' : 'mock-type', 'unit_key' : 'key'}]
        message = 'cannot install this'
        mock_plugins.MOCK_PROFILER.install_units.side_effect = \
            InvalidUnitsRequested(invalid_units, message)
        # Test
        try:
            manager = factory.consumer_agent_manager()
            manager.install_content(self.CONSUMER_ID, invalid_units, {})
            self.fail()
        except PulpDataException, e:
            args = e.data_dict()['args']
            self.assertEqual(args[0], invalid_units)
            self.assertEqual(args[1], message)

    def test_content_update(self):
        # Setup
        self.populate()
        # Test
        unit = dict(type_id='rpm', unit_key=dict(name='zsh'))
        units = [unit,]
        options = {}
        manager = factory.consumer_agent_manager()
        manager.update_content(self.CONSUMER_ID, units, options)
        # Verify
        # # agent call
        params = mock_agent.Content.update.call_args[0]
        self.assertEqual(params[0], units)
        self.assertEqual(params[1], options)
        # profiler call
        profiler = plugin_api.get_profiler_by_type('rpm')[0]
        pargs = profiler.update_units.call_args[0]
        self.assertEquals(pargs[0].id, self.CONSUMER_ID)
        self.assertEquals(pargs[0].profiles, {})
        self.assertEquals(pargs[1], units[:3])
        self.assertEquals(pargs[2], options)

    def test_update_invalid_units(self):
        # Setup
        self.populate()

        invalid_units = [{'type_id' : 'mock-type', 'unit_key' : 'key'}]
        message = 'cannot install this'
        mock_plugins.MOCK_PROFILER.update_units.side_effect = \
            InvalidUnitsRequested(invalid_units, message)
        # Test
        try:
            manager = factory.consumer_agent_manager()
            manager.update_content(self.CONSUMER_ID, invalid_units, {})
            self.fail()
        except PulpDataException, e:
            args = e.data_dict()['args']
            self.assertEqual(args[0], invalid_units)
            self.assertEqual(args[1], message)

    def test_content_uninstall(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_agent_manager()
        unit = dict(type_id='rpm', unit_key=dict(name='zsh'))
        units = [unit,]
        options = {}
        manager.uninstall_content(self.CONSUMER_ID, units, options)
        # Verify
        # agent call
        params = mock_agent.Content.uninstall.call_args[0]
        self.assertEqual(params[0], units)
        self.assertEqual(params[1], options)
        # profiler call
        profiler = plugin_api.get_profiler_by_type('rpm')[0]
        pargs = profiler.uninstall_units.call_args[0]
        self.assertEquals(pargs[0].id, self.CONSUMER_ID)
        self.assertEquals(pargs[0].profiles, {})
        self.assertEquals(pargs[1], units[:3])
        self.assertEquals(pargs[2], options)


    def test_uninstall_invalid_units(self):
        # Setup
        self.populate()

        invalid_units = [{'type_id' : 'mock-type', 'unit_key' : 'key'}]
        message = 'cannot install this'
        mock_plugins.MOCK_PROFILER.uninstall_units.side_effect = \
            InvalidUnitsRequested(invalid_units, message)
        # Test
        try:
            manager = factory.consumer_agent_manager()
            manager.uninstall_content(self.CONSUMER_ID, invalid_units, {})
            self.fail()
        except PulpDataException, e:
            args = e.data_dict()['args']
            self.assertEqual(args[0], invalid_units)
            self.assertEqual(args[1], message)
