# coding=utf-8
"""Tests related to pagination."""
import unittest
from random import sample
from threading import Lock, Thread

from pulp_smash import api, config
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import gen_repo, get_versions

from pulpcore.tests.functional.api.using_plugin.constants import (
    FILE_MANY_FIXTURE_COUNT,
    FILE_MANY_FIXTURE_MANIFEST_URL,
    FILE_CONTENT_PATH
)
from pulpcore.tests.functional.api.using_plugin.utils import populate_pulp
from pulpcore.tests.functional.api.using_plugin.utils import set_up_module as setUpModule  # noqa:F401


class PaginationTestCase(unittest.TestCase):
    """Test pagination.

    This test case assumes that Pulp returns 100 elements in each page of
    results. This is configurable, but the current default set by all known
    Pulp installers.
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.page_handler)

    def test_repos(self):
        """Test pagination for repositories."""
        # Perform a sanity check.
        repos = self.client.get(REPO_PATH)
        self.assertEqual(len(repos), 0, repos)

        # list.append() and list.pop() are thread-safe. ¶ We create 21 repos,
        # because with page_size set to 10, this produces 3 pages, where the
        # three three pages have unique combinations of values for the
        # "previous" and "next" links.
        repo_hrefs = []
        repo_hrefs_lock = Lock()
        number_to_create = 21

        def create_repos():
            """Repeatedly create repos and append to ``repos_hrefs``."""
            # "It's better to beg for forgiveness than to ask for permission."
            while True:
                repo_href = self.client.post(REPO_PATH, gen_repo())['_href']
                with repo_hrefs_lock:
                    if len(repo_hrefs) < number_to_create:
                        repo_hrefs.append(repo_href)
                    else:
                        self.client.delete(repo_href)
                        break

        def delete_repos():
            """Delete the repos listed in ``repos_href``."""
            while True:
                try:
                    self.client.delete(repo_hrefs.pop())
                except IndexError:
                    break

        # Create repos, check results, and delete repos.
        create_threads = tuple(Thread(target=create_repos) for _ in range(4))
        delete_threads = tuple(Thread(target=delete_repos) for _ in range(8))
        try:
            for thread in create_threads:
                thread.start()
            for thread in create_threads:
                thread.join()
            repos = self.client.get(REPO_PATH, params={'page_size': 10})
            self.assertEqual(len(repos), number_to_create, repos)
        finally:
            for thread in delete_threads:
                thread.start()
            for thread in delete_threads:
                thread.join()

    def test_content(self):
        """Test pagination for repository versions."""
        # Add content to Pulp, create a repo, and add content to repo. We
        # sample 21 contents, because with page_size set to 10, this produces 3
        # pages, where the three three pages have unique combinations of values
        # for the "previous" and "next" links.
        populate_pulp(self.cfg, url=FILE_MANY_FIXTURE_MANIFEST_URL)
        sample_size = min(FILE_MANY_FIXTURE_COUNT, 21)
        contents = sample(self.client.get(FILE_CONTENT_PATH), sample_size)
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo['_href'])

        def add_content():
            """Repeatedly pop an item from ``contents``, and add to repo."""
            while True:
                try:
                    content = contents.pop()
                    self.client.post(
                        repo['_versions_href'],
                        {'add_content_units': [content['_href']]}
                    )
                except IndexError:
                    break

        threads = tuple(Thread(target=add_content) for _ in range(8))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify pagination works for getting repo versions.
        repo = self.client.get(repo['_href'])
        repo_versions = get_versions(repo, {'page_size': 10})
        self.assertEqual(len(repo_versions), sample_size, repo_versions)
