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
import copy
import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.common import dateutils
import pulp.server.content.manager as content_manager
from pulp.server.content.distributor.base import Distributor
from pulp.server.db.model.gc_repository import Repo, RepoDistributor
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.publish as publish_manager

# -- mocks --------------------------------------------------------------------

class MockDistributor1(Distributor):

    # Last call state
    repo_data = None
    publish_conduit = None
    distributor_config = None
    repo_config = None

    # Call behavior
    raise_error = False

    def publish_repo(self, repo_data, publish_conduit, distributor_config=None, repo_config=None):
        MockDistributor1.repo_data = repo_data
        MockDistributor1.publish_conduit = publish_conduit
        MockDistributor1.distributor_config = distributor_config
        MockDistributor1.repo_config = repo_config

        if MockDistributor1.raise_error:
            raise Exception('Publish error')

    @classmethod
    def reset(cls):
        MockDistributor1.publish_conduit = None
        MockDistributor1.distributor_config = None
        MockDistributor1.repo_config = None

        MockDistributor1.raise_error = None

class MockDistributor2(Distributor):
    """
    This is kinda ugly but I can't really think of a better way to have a second
    distributor class that will track calls to it.
    """

    # Last call state
    repo_data = None
    publish_conduit = None
    distributor_config = None
    repo_config = None

    # Call behavior
    raise_error = False

    def publish_repo(self, repo_data, publish_conduit, distributor_config=None, repo_config=None):
        MockDistributor2.repo_data = repo_data
        MockDistributor2.publish_conduit = publish_conduit
        MockDistributor2.distributor_config = distributor_config
        MockDistributor2.repo_config = repo_config

        if MockDistributor2.raise_error:
            raise Exception('Publish error')

    @classmethod
    def reset(cls):
        MockDistributor2.publish_conduit = None
        MockDistributor2.distributor_config = None
        MockDistributor2.repo_config = None

        MockDistributor2.raise_error = None

# -- test cases ---------------------------------------------------------------

class RepoSyncManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)

        content_manager._create_manager()

        # Configure content manager
        content_manager._MANAGER.add_distributor('MockDistributor1', 1, MockDistributor1, None)
        content_manager._MANAGER.add_distributor('MockDistributor2', 1, MockDistributor2, None)

        # Create the manager instances for testing
        self.repo_manager = repo_manager.RepoManager()
        self.publish_manager = publish_manager.RepoPublishManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)

        # Reset content manager
        content_manager._MANAGER.remove_distributor('MockDistributor1', 1)
        content_manager._MANAGER.remove_distributor('MockDistributor2', 1)

    def clean(self):
        testutil.PulpTest.clean(self)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()

        # Reset the state of the mock's tracker variables
        MockDistributor1.reset()
        MockDistributor2.reset()

    def test_publish(self):
        """
        Tests publish under normal conditions when everything is configured
        correctly.
        """

        # Setup
        publish_config = {'foo' : 'bar'}
        self.repo_manager.create_repo('repo-1')
        self.repo_manager.add_distributor('repo-1', 'MockDistributor1', publish_config, False, distributor_id='dist-1')
        self.repo_manager.add_distributor('repo-1', 'MockDistributor2', publish_config, False, distributor_id='dist-2')

        # Test
        self.publish_manager.publish('repo-1', 'dist-1', None)

        # Verify

        #   Database
        repo_distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'repo-1', 'id' : 'dist-1'})
        self.assertTrue(not repo_distributor['publish_in_progress'])
        self.assertTrue(repo_distributor['last_publish'] is not None)
        self.assertTrue(assert_last_sync_time(repo_distributor['last_publish']))

        #   Call into the correct distributor
        self.assertEqual('repo-1', MockDistributor1.repo_data['id'])
        self.assertEqual(publish_config, MockDistributor1.repo_config)
        self.assertTrue(MockDistributor1.publish_conduit is not None)

        self.assertTrue(MockDistributor2.repo_data is None)
        self.assertTrue(MockDistributor2.distributor_config is None)
        self.assertTrue(MockDistributor2.publish_conduit is None)

    def test_publish_with_config_override(self):
        """
        Tests a publish when passing in override values.
        """

        # Setup
        distributor_config = {'key-1' : 'orig-1', 'key-2' : 'orig-2'}
        self.repo_manager.create_repo('repo-1')
        self.repo_manager.add_distributor('repo-1', 'MockDistributor2', distributor_config, False, 'dist-2')

        # Test
        publish_overrides = {'key-1' : 'new-1', 'key-3' : 'new-3'}
        self.publish_manager.publish('repo-1', 'dist-2', publish_overrides)

        # Verify call into mock
        expected_config = copy.copy(distributor_config)
        expected_config.update(publish_overrides)
        self.assertEqual(expected_config, MockDistributor2.repo_config)

    def test_publish_missing_repo(self):
        """
        Tests the proper error is raised when a non-existent repo is specified.
        """

        # Test
        try:
            self.publish_manager.publish('not-here', 'doesnt-matter', None)
        except publish_manager.MissingRepo, e:
            self.assertEqual('not-here', e.repo_id)
            print(e) # for coverage

    def test_publish_no_distributor(self):
        """
        Tests the proper error is raised when a non-existed distributor is specified.
        """

        # Setup
        self.repo_manager.create_repo('no-dist')

        # Test
        try:
            self.publish_manager.publish('no-dist', 'fake-dist')
        except publish_manager.NoDistributor, e:
            self.assertEqual('no-dist', e.repo_id)
            print(e) # for coverage

    def test_publish_bad_distributor(self):
        """
        Tests the proper error is raised when a distributor is set but the distributor
        is no longer present as a plugin.
        """

        # Setup
        self.repo_manager.create_repo('repo')
        self.repo_manager.add_distributor('repo', 'MockDistributor1', None, False, distributor_id='dist-1')

        #   Simulate bouncing the server and removing the distributor plugin
        content_manager._MANAGER.remove_distributor('MockDistributor1', 1)

        # Test
        try:
            self.publish_manager.publish('repo', 'dist-1', None)
        except publish_manager.MissingDistributorPlugin, e:
            self.assertEqual('repo', e.repo_id)
            print(e) # for coverage

    def test_publish_bad_database(self):
        """
        Tests the case where the database is in a bad state and no longer has the
        repo-distributor relationship collection.
        """

        # Setup
        self.repo_manager.create_repo('repo')
        self.repo_manager.add_distributor('repo', 'MockDistributor1', None, False, distributor_id='dist-1')

        RepoDistributor.get_collection().remove()

        # Test
        try:
            self.publish_manager.publish('repo', 'dist-1')
        except publish_manager.NoDistributor, e:
            self.assertEqual('repo', e.repo_id)
            print(e) # for coverage
        
    def test_publish_with_error(self):
        """
        Tests a publish when the plugin raises an error.
        """

        # Setup
        MockDistributor1.raise_error = True

        self.repo_manager.create_repo('gonna-bail')
        self.repo_manager.add_distributor('gonna-bail', 'MockDistributor1', None, False, distributor_id='bad-dist')

        # Test
        try:
            self.publish_manager.publish('gonna-bail', 'bad-dist')
        except publish_manager.RepoPublishException, e:
            self.assertEqual('gonna-bail', e.repo_id)
            print(e) # for coverage

        # Verify
        repo_distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'gonna-bail', 'id' : 'bad-dist'})

        self.assertTrue(not repo_distributor['publish_in_progress'])
        self.assertTrue(repo_distributor is not None)
        self.assertTrue(assert_last_sync_time(repo_distributor['last_publish']))


    def test_publish_in_progress(self):
        """
        Tests trying to publish while one is in progress raises the correct error.
        """

        # Setup
        self.repo_manager.create_repo('busy')
        self.repo_manager.add_distributor('busy', 'MockDistributor1', {}, False, 'dist-1')

        #   Trick the database into thinking it's publishing
        repo_distributor = RepoDistributor.get_collection().find_one({'repo_id' : 'busy'})
        repo_distributor['publish_in_progress'] = True
        RepoDistributor.get_collection().save(repo_distributor)

        # Test
        try:
            self.publish_manager.publish('busy', 'dist-1')
        except publish_manager.PublishInProgress, e:
            self.assertEqual('busy', e.repo_id)
            print(e) # for coverage

# -- testing utilities --------------------------------------------------------

def assert_last_sync_time(time_in_iso):
    now = datetime.datetime.now(dateutils.local_tz())
    finished = dateutils.parse_iso8601_datetime(time_in_iso)

    # Compare them within a threshold since they won't be exact
    difference = now - finished
    return difference.seconds < 2