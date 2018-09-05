# coding=utf-8
"""Tests that perform actions over publications."""
import unittest

from requests.exceptions import HTTPError

from pulp_smash import api, config
from pulp_smash.pulp3.constants import DISTRIBUTION_PATH, PUBLICATIONS_PATH, REPO_PATH
from pulp_smash.pulp3.utils import (
    gen_distribution,
    gen_repo,
    publish,
    sync,
)

from tests.functional.api.using_plugin.constants import (
    FILE_PUBLISHER_PATH,
    FILE_REMOTE_PATH
)
from tests.functional.api.using_plugin.utils import (
    gen_file_publisher,
    gen_file_remote,
    skip_if
)
from tests.functional.api.using_plugin.utils import set_up_module as setUpModule  # noqa:F401


class PublicationsTestCase(unittest.TestCase):
    """Perform actions over publications."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.page_handler)
        cls.remote = {}
        cls.publication = {}
        cls.publisher = {}
        cls.repo = {}
        try:
            cls.repo.update(cls.client.post(REPO_PATH, gen_repo()))
            body = gen_file_remote()
            cls.remote.update(cls.client.post(FILE_REMOTE_PATH, body))
            cls.publisher.update(
                cls.client.post(FILE_PUBLISHER_PATH, gen_file_publisher())
            )
            sync(cls.cfg, cls.remote, cls.repo)
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variables."""
        for resource in (cls.remote, cls.publisher, cls.repo):
            if resource:
                cls.client.delete(resource['_href'])

    def test_01_create_publication(self):
        """Create a publication."""
        self.publication.update(
            publish(self.cfg, self.publisher, self.repo)
        )

    @skip_if(bool, 'publication', False)
    def test_02_read_publication(self):
        """Read a publication by its href."""
        publication = self.client.get(self.publication['_href'])
        for key, val in self.publication.items():
            with self.subTest(key=key):
                self.assertEqual(publication[key], val)

    @skip_if(bool, 'publication', False)
    def test_02_read_publications(self):
        """Read a publication by its repository version."""
        publications = self.client.get(PUBLICATIONS_PATH, params={
            'repository_version': self.repo['_href']
        })
        self.assertEqual(len(publications), 1, publications)
        for key, val in self.publication.items():
            with self.subTest(key=key):
                self.assertEqual(publications[0][key], val)

    @skip_if(bool, 'publication', False)
    def test_03_read_publications(self):
        """Read a publication by its publisher."""
        publications = self.client.get(PUBLICATIONS_PATH, params={
            'publisher': self.publisher['_href']
        })
        self.assertEqual(len(publications), 1, publications)
        for key, val in self.publication.items():
            with self.subTest(key=key):
                self.assertEqual(publications[0][key], val)

    @skip_if(bool, 'publication', False)
    def test_04_read_publications(self):
        """Read a publication by its created time."""
        publications = self.client.get(PUBLICATIONS_PATH, params={
            'created': self.publication['created']
        })
        self.assertEqual(len(publications), 1, publications)
        for key, val in self.publication.items():
            with self.subTest(key=key):
                self.assertEqual(publications[0][key], val)

    @skip_if(bool, 'publication', False)
    def test_05_read_publications(self):
        """Read a publication by its distribution."""
        body = gen_distribution()
        body['publication'] = self.publication['_href']
        distribution = self.client.post(DISTRIBUTION_PATH, body)
        self.addCleanup(self.client.delete, distribution['_href'])

        self.publication.update(self.client.get(self.publication['_href']))
        publications = self.client.get(PUBLICATIONS_PATH, params={
            'distributions': distribution['_href']
        })
        self.assertEqual(len(publications), 1, publications)
        for key, val in self.publication.items():
            with self.subTest(key=key):
                self.assertEqual(publications[0][key], val)

    @skip_if(bool, 'publication', False)
    def test_06_delete(self):
        """Delete a publication."""
        self.client.delete(self.publication['_href'])
        with self.assertRaises(HTTPError):
            self.client.get(self.publication['_href'])
