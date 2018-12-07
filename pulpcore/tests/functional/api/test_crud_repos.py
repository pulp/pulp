# coding=utf-8
"""Tests that CRUD repositories."""
import unittest

from itertools import permutations
from requests.exceptions import HTTPError

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import gen_repo

from pulpcore.tests.functional.utils import set_up_module as setUpModule  # noqa:F401
from pulpcore.tests.functional.utils import skip_if


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

        * `Pulp Smash #882 <https://github.com/PulpQE/pulp-smash/issues/882>`_.
        * `Pulp Smash #1055
        <https://github.com/PulpQE/pulp-smash/issues/1055>`_.
        """
        self.client.response_handler = api.echo_handler
        response = self.client.post(
            REPO_PATH,
            gen_repo(name=self.repo['name'])
        )
        self.assertIn('unique', response.json()['name'][0])
        self.assertEqual(response.status_code, 400)

    @skip_if(bool, 'repo', False)
    def test_02_read_repo(self):
        """Read a repository by its href."""
        repo = self.client.get(self.repo['_href'])
        for key, val in self.repo.items():
            with self.subTest(key=key):
                self.assertEqual(repo[key], val)

    @skip_if(bool, 'repo', False)
    def test_02_read_repo_with_specific_fields(self):
        """Read a repository by its href providing specific field list.

        Permutate field list to ensure different combinations on result.
        """
        fields = (
            '_href', 'created', '_versions_href', '_latest_version_href',
            'name', 'description'
        )
        for field_pair in permutations(fields, 2):
            # ex: field_pair = ('_href', 'created')
            with self.subTest(field_pair=field_pair):
                repo = self.client.get(
                    self.repo['_href'],
                    params={'fields': ','.join(field_pair)}
                )
                self.assertEqual(sorted(field_pair), sorted(repo.keys()))

    @skip_if(bool, 'repo', False)
    def test_02_read_repo_without_specific_fields(self):
        """Read a repo by its href excluding specific fields."""
        # requests doesn't allow the use of != in parameters.
        url = '{}?fields!=created,name'.format(self.repo['_href'])
        repo = self.client.get(url)
        response_fields = repo.keys()
        self.assertNotIn('created', response_fields)
        self.assertNotIn('name', response_fields)

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

    def test_negative_create_repo_with_invalid_parameter(self):
        """Attempt to create repository passing extraneous invalid parameter.

        Assert response returns an error 400 including ["Unexpected field"].
        """
        response = api.Client(self.cfg, api.echo_handler).post(
            REPO_PATH, gen_repo(foo='bar')
        )
        assert response.status_code == 400
        assert response.json()['foo'] == ['Unexpected field']
