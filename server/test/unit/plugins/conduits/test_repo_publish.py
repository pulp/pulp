import datetime

import mock

from ... import base
from pulp.common import dateutils
from pulp.devel import mock_plugins
from pulp.plugins.conduits.mixins import DistributorConduitException
from pulp.plugins.conduits.repo_publish import RepoPublishConduit, RepoGroupPublishConduit
from pulp.server.db import model
from pulp.server.db.model.repo_group import RepoGroup, RepoGroupDistributor
from pulp.server.db.model.repository import RepoDistributor
from pulp.server.managers import factory as manager_factory


class RepoPublishConduitTests(base.PulpServerTests):

    def clean(self):
        super(RepoPublishConduitTests, self).clean()

        mock_plugins.reset()
        model.Repository.drop_collection()
        RepoDistributor.get_collection().remove()

    @mock.patch('pulp.server.managers.repo.distributor.model.Repository.objects')
    def setUp(self, mock_repo_qs):
        super(RepoPublishConduitTests, self).setUp()
        mock_plugins.install()
        manager_factory.initialize()

        self.distributor_manager = manager_factory.repo_distributor_manager()

        # Populate the database with a repo with units
        self.distributor_manager.add_distributor('repo-1', 'mock-distributor', {}, True,
                                                 distributor_id='dist-1')

        self.conduit = RepoPublishConduit('repo-1', 'dist-1')

    def tearDown(self):
        super(RepoPublishConduitTests, self).tearDown()
        mock_plugins.reset()

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
        last_publish = datetime.datetime(2015, 4, 29, 20, 23, 56, 0)
        repo_dist = RepoDistributor.get_collection().find_one({'repo_id': 'repo-1'})
        repo_dist['last_publish'] = last_publish
        RepoDistributor.get_collection().save(repo_dist)

        # Test - Last publish
        found = self.conduit.last_publish()
        self.assertTrue(isinstance(found, datetime.datetime))  # check returned format

        self.assertEqual(found.tzinfo, dateutils.utc_tz())
        self.assertEqual(repo_dist['last_publish'], found.replace(tzinfo=None))

    @mock.patch('pulp.plugins.conduits.repo_publish.RepoDistributor')
    def test_last_publish_with_error(self, mock_dist):
        """
        Test the handling of an error getting last_publish information.
        """
        mock_dist.get_collection().find_one.return_value = None
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
        distributor = self.distributor_manager.add_distributor(
            self.group_id, 'mock-group-distributor', {}, distributor_id=self.distributor_id)

        self.conduit = RepoGroupPublishConduit(self.group_id, distributor)

    def tearDown(self):
        super(RepoGroupPublishConduitTests, self).tearDown()
        mock_plugins.reset()

    def test_str(self):
        self.assertEqual(str(self.conduit), 'RepoGroupPublishConduit for group [conduit-group]')

    def test_last_publish(self):
        # Test - Unpublished
        unpublished = self.conduit.last_publish()
        self.assertTrue(unpublished is None)

        last_publish = datetime.datetime.now()
        repo_group_dist = self.distributor_manager.get_distributor(self.group_id,
                                                                   self.distributor_id)
        repo_group_dist['last_publish'] = dateutils.format_iso8601_datetime(last_publish)
        RepoGroupDistributor.get_collection().save(repo_group_dist)

        # Test
        found = self.conduit.last_publish()
        self.assertTrue(isinstance(found, datetime.datetime))
        # simulate the DB encoding
        last_publish = dateutils.parse_iso8601_datetime(repo_group_dist['last_publish'])
        self.assertEqual(last_publish, found)

    @mock.patch('pulp.server.managers.repo.group.publish.RepoGroupPublishManager.last_publish')
    def test_last_publish_server_error(self, mock_call):
        mock_call.side_effect = Exception()
        self.assertRaises(DistributorConduitException, self.conduit.last_publish)
