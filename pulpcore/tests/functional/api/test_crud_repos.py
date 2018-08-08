# coding=utf-8
"""Tests that CRUD repositories."""
import unittest

from requests.exceptions import HTTPError

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import gen_repo

from tests.functional.utils import set_up_module as setUpModule  # noqa:F401
from tests.functional.utils import skip_if


class CRUDRepoTestCase(unittest.TestCase):
    """CRUD repositories."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.repo = {}

    def setUp(self):
        """Create an API client."""
        self.client = api.Client(self.cfg, api.json_handler)

    def test_01_create_repo(self):
        """Create repository."""
        type(self).repo = self.client.post(REPO_PATH, gen_repo())

    @skip_if(bool, 'repo', False)
    def test_02_create_same_name(self):
        """Try to create a second repository with an identical name.

        See: `Pulp Smash #1055
        <https://github.com/PulpQE/pulp-smash/issues/1055>`_.
        """
        body = gen_repo()
        body['name'] = self.repo['name']
        with self.assertRaises(HTTPError):
            self.client.post(REPO_PATH, body)

    @skip_if(bool, 'repo', False)
    def test_02_read_repo(self):
        """Read a repository by its href."""
        repo = self.client.get(self.repo['_href'])
        for key, val in self.repo.items():
            with self.subTest(key=key):
                self.assertEqual(repo[key], val)

    @skip_if(bool, 'repo', False)
    def test_02_read_repos(self):
        """Read the repository by its name."""
        page = self.client.get(REPO_PATH, params={
            'name': self.repo['name']
        })
        self.assertEqual(len(page['results']), 1)
        for key, val in self.repo.items():
            with self.subTest(key=key):
                self.assertEqual(page['results'][0][key], val)

    @skip_if(bool, 'repo', False)
    def test_02_read_all_repos(self):
        """Ensure name is displayed when listing repositories.

        See Pulp #2824 <https://pulp.plan.io/issues/2824>`_
        """
        for repo in self.client.get(REPO_PATH)['results']:
            self.assertIsNotNone(repo['name'])

    @skip_if(bool, 'repo', False)
    def test_03_fully_update_name(self):
        """Update a repository's name using HTTP PUT.

        See: `Pulp #3101 <https://pulp.plan.io/issues/3101>`_
        """
        self.do_fully_update_attr('name')

    @skip_if(bool, 'repo', False)
    def test_03_fully_update_desc(self):
        """Update a repository's description using HTTP PUT."""
        self.do_fully_update_attr('description')

    def do_fully_update_attr(self, attr):
        """Update a repository attribute using HTTP PUT.

        :param attr: The name of the attribute to update. For example,
            "description." The attribute to update must be a string.
        """
        repo = self.client.get(self.repo['_href'])
        string = utils.uuid4()
        repo[attr] = string
        self.client.put(repo['_href'], repo)

        # verify the update
        repo = self.client.get(repo['_href'])
        self.assertEqual(string, repo[attr])

    @skip_if(bool, 'repo', False)
    def test_03_partially_update_name(self):
        """Update a repository's name using HTTP PATCH.

        See: `Pulp #3101 <https://pulp.plan.io/issues/3101>`_
        """
        self.do_partially_update_attr('name')

    @skip_if(bool, 'repo', False)
    def test_03_partially_update_desc(self):
        """Update a repository's description using HTTP PATCH."""
        self.do_partially_update_attr('description')

    def do_partially_update_attr(self, attr):
        """Update a repository attribute using HTTP PATCH.

        :param attr: The name of the attribute to update. For example,
            "description." The attribute to update must be a string.
        """
        string = utils.uuid4()
        self.client.patch(self.repo['_href'], {attr: string})

        # verify the update
        repo = self.client.get(self.repo['_href'])
        self.assertEqual(repo[attr], string)

    @skip_if(bool, 'repo', False)
    def test_04_delete_repo(self):
        """Delete a repository."""
        self.client.delete(self.repo['_href'])

        # verify the delete
        with self.assertRaises(HTTPError):
            self.client.get(self.repo['_href'])
