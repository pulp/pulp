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

import datetime
import mock

import base
import mock_plugins

from pulp.common import dateutils
from pulp.plugins.conduits.mixins import DistributorConduitException
from pulp.plugins.conduits.repo_publish import RepoPublishConduit, RepoGroupPublishConduit
from pulp.server.db.model.repo_group import RepoGroup, RepoGroupDistributor
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.managers import factory as manager_factory

# -- test cases ---------------------------------------------------------------

class RepoPublishConduitTests(base.PulpServerTests):

    def clean(self):
        super(RepoPublishConduitTests, self).clean()

        mock_plugins.reset()

        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()

    def setUp(self):
        super(RepoPublishConduitTests, self).setUp()
        mock_plugins.install()
        manager_factory.initialize()

        self.repo_manager = manager_factory.repo_manager()
        self.distributor_manager = manager_factory.repo_distributor_manager()

        # Populate the database with a repo with units
        self.repo_manager.create_repo('repo-1')
        self.distributor_manager.add_distributor('repo-1', 'mock-distributor', {}, True, distributor_id='dist-1')

        self.conduit = RepoPublishConduit('repo-1', 'dist-1')

    def test_str(self):
        """
        Makes sure the __str__ implementation doesn't crash.
        """
        str(self.conduit)

    def test_last_publish(self):
        """
        Tests retrieving the last publish time in both the unpublish and previously published cases.
        """

        # Test - Unpublished
        unpublished = self.conduit.last_publish()
        self.assertTrue(unpublished is None)

        # Setup - Previous publish
        last_publish = datetime.datetime.now()
        repo_dist = RepoDistributor.get_collection().find_one({'repo_id' : 'repo-1'})
        repo_dist['last_publish'] = dateutils.format_iso8601_datetime(last_publish)
        RepoDistributor.get_collection().save(repo_dist, safe=True)

        # Test - Last publish
        found = self.conduit.last_publish()
        self.assertTrue(isinstance(found, datetime.datetime)) # check returned format
        self.assertEqual(repo_dist['last_publish'], dateutils.format_iso8601_datetime(found))

    @mock.patch('pulp.server.managers.repo.publish.RepoPublishManager.last_publish')
    def test_last_publish_with_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(DistributorConduitException, self.conduit.last_publish)

class RepoGroupPublishConduitTests(base.PulpServerTests):
    def clean(self):
        super(RepoGroupPublishConduitTests, self).clean()

        RepoGroup.get_collection().remove()
        RepoGroupDistributor.get_collection().remove()

    def setUp(self):
        super(RepoGroupPublishConduitTests, self).setUp()
        mock_plugins.install()
        manager_factory.initialize()

        self.group_manager = manager_factory.repo_group_manager()
        self.distributor_manager = manager_factory.repo_group_distributor_manager()

        self.group_id = 'conduit-group'
        self.distributor_id = 'conduit-distributor'

        self.group_manager.create_repo_group(self.group_id)
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id=self.distributor_id)

        self.conduit = RepoGroupPublishConduit(self.group_id, self.distributor_id)

    def test_str(self):
        str(self.conduit) # make sure no exception is raised

    def test_last_publish(self):
        # Test - Unpublished
        unpublished = self.conduit.last_publish()
        self.assertTrue(unpublished is None)

        # Setup - Publish
        last_publish = datetime.datetime.now()
        repo_group_dist = self.distributor_manager.get_distributor(self.group_id, self.distributor_id)
        repo_group_dist['last_publish'] = dateutils.format_iso8601_datetime(last_publish)
        RepoGroupDistributor.get_collection().save(repo_group_dist, safe=True)

        # Test
        found = self.conduit.last_publish()
        self.assertTrue(isinstance(found, datetime.datetime))

        last_publish = dateutils.parse_iso8601_datetime(repo_group_dist['last_publish']) # simulate the DB encoding
        self.assertEqual(last_publish, found)

    @mock.patch('pulp.server.managers.repo.group.publish.RepoGroupPublishManager.last_publish')
    def test_last_publish_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(DistributorConduitException, self.conduit.last_publish)
