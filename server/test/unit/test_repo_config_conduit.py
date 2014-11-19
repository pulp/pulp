import base
from operator import itemgetter

from pulp.devel import mock_plugins
from pulp.plugins.conduits.repo_config import RepoConfigConduit
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.managers import factory as manager_factory


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
        self.repo_manager.create_repo('repo-3')
        self.distributor_manager.add_distributor('repo-3', 'mock-distributor', {},
                                                 True, distributor_id='dist-4')
        self.repo_manager.create_repo('repo-4')
        self.distributor_manager.add_distributor('repo-4', 'mock-distributor', {"relative_url": "repo-5"},
                                                 True, distributor_id='dist-5')
        self.repo_manager.create_repo('repo-5')
        self.distributor_manager.add_distributor('repo-5', 'mock-distributor', {"relative_url": "a/bcd/e"},
                                                 True, distributor_id='dist-1')
        self.repo_manager.create_repo('repo-6')
        self.distributor_manager.add_distributor('repo-6', 'mock-distributor', {"relative_url": "a/bcde/f/"},
                                                 True, distributor_id='dist-1')

        self.conduit = RepoConfigConduit('rpm')

    def tearDown(self):
        super(RepoConfigConduitTests, self).tearDown()
        mock_plugins.reset()

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

        self.assertEquals(matches.count(), 1)
        self.assertEquals(next(matches)['repo_id'], 'repo-1')

        matches = self.conduit.get_repo_distributors_by_relative_url("a/bc/d")

        self.assertEquals(matches.count(), 1)
        self.assertEquals(next(matches)['repo_id'], 'repo-1')

        matches = self.conduit.get_repo_distributors_by_relative_url("a/bc/d/")

        self.assertEquals(matches.count(), 1)
        self.assertEquals(next(matches)['repo_id'], 'repo-1')

    def test_get_distributors_by_relative_url_with_with_excluded_repository_id(self):
        """
        Test for distributors with a matching url but excluded because of the repo_id
        """
        matches = self.conduit.get_repo_distributors_by_relative_url("/a/bc/d", 'repo-1')
        self.assertEquals(matches.count(), 0)

        matches = self.conduit.get_repo_distributors_by_relative_url("a/bc/d", 'repo-1')
        self.assertEquals(matches.count(), 0)

        matches = self.conduit.get_repo_distributors_by_relative_url("a/bc/d/", 'repo-1')
        self.assertEquals(matches.count(), 0)

    def test_get_distributors_by_relative_url_with_different_url(self):
        """
        Test for distributors with no matching relative url
        """
        matches = self.conduit.get_repo_distributors_by_relative_url("/d")
        self.assertEquals(matches.count(), 0)

        matches = self.conduit.get_repo_distributors_by_relative_url("d")
        self.assertEquals(matches.count(), 0)

        matches = self.conduit.get_repo_distributors_by_relative_url("d/")
        self.assertEquals(matches.count(), 0)

    def test_get_distributors_by_relative_url_with_superset_url(self):
        """
        Test for distributors with urls that be overridden by the proposed relative url
        """
        matches = self.conduit.get_repo_distributors_by_relative_url("/a/bc")
        self.assertEquals(matches.count(), 2)
        #verify that the correct 2 repositories were found
        matches = sorted(list(matches), key=itemgetter('repo_id'))
        self.assertEquals(matches[0]['repo_id'], 'repo-1')
        self.assertEquals(matches[1]['repo_id'], 'repo-2')

        matches = self.conduit.get_repo_distributors_by_relative_url("a/bc")
        self.assertEquals(matches.count(), 2)
        #verify that the correct 2 repositories were found
        matches = sorted(list(matches), key=itemgetter('repo_id'))
        self.assertEquals(matches[0]['repo_id'], 'repo-1')
        self.assertEquals(matches[1]['repo_id'], 'repo-2')

        matches = self.conduit.get_repo_distributors_by_relative_url("a/bc/")
        self.assertEquals(matches.count(), 2)
        #verify that the correct 2 repositories were found
        matches = sorted(list(matches), key=itemgetter('repo_id'))
        self.assertEquals(matches[0]['repo_id'], 'repo-1')
        self.assertEquals(matches[1]['repo_id'], 'repo-2')

    def test_get_distributors_by_relative_url_with_subset_url(self):
        """
        Test for distributors with urls that would override the proposed relative url
        """
        matches = self.conduit.get_repo_distributors_by_relative_url("a/bc/d/e")
        self.assertEquals(matches.count(), 1)
        self.assertEquals(next(matches)['repo_id'], 'repo-1')

        matches = self.conduit.get_repo_distributors_by_relative_url("a/bc/d/e")
        self.assertEquals(matches.count(), 1)
        self.assertEquals(next(matches)['repo_id'], 'repo-1')

        matches = self.conduit.get_repo_distributors_by_relative_url("a/bc/d/e/")
        self.assertEquals(matches.count(), 1)
        self.assertEquals(next(matches)['repo_id'], 'repo-1')

    def test_get_distributors_with_no_relative_url(self):
        """
        Test for distributors where no relative url is specified, the distributor id is used
        in it's place
        """
        matches = self.conduit.get_repo_distributors_by_relative_url("/repo-3")
        self.assertEquals(matches.count(), 1)
        self.assertEquals(next(matches)['repo_id'], 'repo-3')

        matches = self.conduit.get_repo_distributors_by_relative_url("repo-3")
        self.assertEquals(matches.count(), 1)
        self.assertEquals(next(matches)['repo_id'], 'repo-3')

        matches = self.conduit.get_repo_distributors_by_relative_url("repo-3/")
        self.assertEquals(matches.count(), 1)
        self.assertEquals(next(matches)['repo_id'], 'repo-3')

    def test_get_distributors_without_leading_or_trailing_slash_relative_url(self):
        """
        Test matching repos that include preceding slashes with a search that doesn't include
        preceding and trailing slashes.
        """

        matches = self.conduit.get_repo_distributors_by_relative_url("a/bcd/e")

        self.assertEqual(matches.count(), 1)
        self.assertEqual(next(matches)['repo_id'], 'repo-5')

    def test_get_distributors_without_leading_slash_relative_url(self):
        """
        Test matching repos that do not include preceding slashes with a search that doesn't
        include preceding and trailing slashes.
        """

        matches = self.conduit.get_repo_distributors_by_relative_url("a/bcde/f")

        self.assertEqual(matches.count(), 1)
        self.assertEqual(next(matches)['repo_id'], 'repo-6')

    def test_get_distributors_url_does_not_conflict_with_repo_id(self):
        """
        Test matching repos with a defined relative-url using their repo id instead of relative-url.
        """
        matches = self.conduit.get_repo_distributors_by_relative_url("repo-1")

        self.assertEqual(matches.count(), 0)
