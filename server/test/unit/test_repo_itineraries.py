# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from base import PulpItineraryTests
from pulp.devel import mock_plugins
from pulp.devel import mock_agent
from pulp.plugins.loader import api as plugin_api
from pulp.server.managers import factory
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.itineraries.repository import *


class TestDeletes(PulpItineraryTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'dist-1'
    NOTIFY_AGENT = True
    BINDING_CONFIG = {'d' : 'd'}
    DISTRIBUTOR_TYPE_ID = 'mock-distributor'

    def setUp(self):
        PulpItineraryTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()
        mock_agent.install()

    def tearDown(self):
        PulpItineraryTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        manager = factory.repo_manager()
        manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(self.REPO_ID, self.DISTRIBUTOR_TYPE_ID, {}, True,
                                distributor_id=self.DISTRIBUTOR_ID)
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)

    def test_repo_delete(self):

        # Setup
        self.populate()

        # Test

        itinerary = repo_delete_itinerary(self.REPO_ID)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify

        self.assertEqual(len(call_reports), 4)
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1: repo delete
        self.run_next()

        # verify repo deleted
        repo = Repo.get_collection().find_one({'id' : self.REPO_ID})
        self.assertTrue(repo is None)

    def test_distributor_delete(self):

        # Setup
        self.populate()

        # Test

        itinerary = distributor_delete_itinerary(self.REPO_ID, self.DISTRIBUTOR_ID)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify

        self.assertEqual(len(call_reports), 4)
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1: distributor delete
        self.run_next()

        # verify distributor deleted
        dist = RepoDistributor.get_collection().find_one({'repo_id' : self.REPO_ID})
        self.assertTrue(dist is None)

    def test_distributor_update(self):

        # Setup
        self.populate()

        # Test

        new_config = {'A':1, 'B':2}
        itinerary = distributor_update_itinerary(self.REPO_ID, self.DISTRIBUTOR_ID, new_config)
        call_reports = self.coordinator.execute_multiple_calls(itinerary)

        # Verify

        self.assertEqual(len(call_reports), 3)
        for call in call_reports:
            self.assertNotEqual(call.state, dispatch_constants.CALL_REJECTED_RESPONSE)

        # run task #1: distributor update
        self.run_next()

        # verify distributor updated
        dist = RepoDistributor.get_collection().find_one({'repo_id' : self.REPO_ID})
        self.assertEqual(new_config, dict(dist['config']))

    def test_distributor_update_auto_publish(self):
        # Setup
        self.populate()
        new_config = {'key': 'value'}
        delta = {'auto_publish': False}
        expected_kwargs = {'auto_publish': False, 'distributor_config': new_config}

        # Test that the keyword arguments for the CallRequest contain the expected values
        itinerary = distributor_update_itinerary(self.REPO_ID, self.DISTRIBUTOR_ID, new_config, delta)
        self.assertEqual(expected_kwargs, itinerary[0].kwargs)
