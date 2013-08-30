#!/usr/bin/python
#
# Copyright © 2011 Red Hat, Inc.
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

"""
Test Cases for the Repo Config Conduit

"""

import base
import mock_plugins

from pulp.plugins.conduits.repo_config import RepoConfigConduit
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.managers import factory as manager_factory

# -- test cases ---------------------------------------------------------------

class RepoConfigConduitTests(base.PulpServerTests):

    def setUp(self):
        super(RepoConfigConduitTests, self).setUp()
        mock_plugins.install()
        manager_factory.initialize()

        self.repo_manager = manager_factory.repo_manager()
        self.distributor_manager = manager_factory.repo_distributor_manager()

        # Populate the database with a repo with units
        self.repo_manager.create_repo('repo-1')
        self.distributor_manager.add_distributor('repo-1', 'mock-distributor', {"relative_url": "/a/bc/d"},
                                                 True, distributor_id='dist-1')
        self.distributor_manager.add_distributor('repo-1', 'mock-distributor', {"relative_url": "/a/c"},
                                                 True, distributor_id='dist-2')
        self.repo_manager.create_repo('repo-2')
        self.distributor_manager.add_distributor('repo-2', 'mock-distributor', {"relative_url": "/a/bc/e"},
                                                 True, distributor_id='dist-3')

        self.conduit = RepoConfigConduit('rpm')

    def clean(self):
        super(RepoConfigConduitTests, self).clean()

        mock_plugins.MOCK_DISTRIBUTOR.reset_mock()

        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()


    def test_get_distributors_by_relative_url_with_same_url(self):
        """
        Test for distributors with an identical relative url
        """
        matches = self.conduit.get_repo_distributors_by_relative_url("/a/bc/d")
        self.assertEquals(len(matches), 1)

    def test_get_distributors_by_relative_url_with_different_url(self):
        """
        Test for distributors with no matching relative url
        """
        matches = self.conduit.get_repo_distributors_by_relative_url("/d")
        self.assertEquals(len(matches), 0)

    def test_get_distributors_by_relative_url_with_superset_url(self):
        """
        Test for distributors with urls that be overridden by the proposed relative url
        """
        matches = self.conduit.get_repo_distributors_by_relative_url("/a/bc")
        self.assertEquals(len(matches), 2)

    def test_get_distributors_by_relative_url_with_subset_url(self):
        """
        Test for distributors with urls that would override the proposed relative url
        """
        matches = self.conduit.get_repo_distributors_by_relative_url("/a/bc/d/e")
        self.assertEquals(len(matches), 1)
