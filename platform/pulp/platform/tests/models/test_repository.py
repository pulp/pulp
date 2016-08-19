"""
These tests are intended to be a HOW TO for working with the repository motel.
"""

from django.test import TestCase

from pulp.platform.models import Repository, RepositoryImporter, RepositoryDistributor


class TestRepository(TestCase):

    NAME = 'zoo'

    def _create_repository(self):
        """
        Create a repository with sample notes and scratchpad.
        """
        repository = Repository(name=TestRepository.NAME)
        repository.notes.mapping['organization'] = 'Engineering'
        repository.notes.mapping.update({'age': 10})
        repository.scratchpad.mapping['hello'] = 'world'
        repository.save()

    def _delete_repository(self):
        """
        Delete the repository.
        """
        repository = Repository.objects.filter(name=TestRepository.NAME)
        repository.delete()

    def _add_importer(self):
        """
        Add an importer with feed URL and some standard settings.
        """
        repository = Repository.objects.get(name=TestRepository.NAME)
        importer = RepositoryImporter(repository=repository)
        importer.name = 'Upstream'
        importer.type = 'YUM'
        importer.feed_url = 'http://content-world/everyting/'
        importer.ssl_validation = True
        importer.ssl_ca_certificate = 'MY-CA'
        importer.ssl_client_certificate = 'MY-CERTIFICATE'
        importer.ssl_client_key = 'MY-KEY'
        importer.proxy_url = 'http://elmer:fudd@warnerbrothers.com'
        importer.basic_auth_user = 'Elmer'
        importer.basic_auth_password = 'Fudd'
        importer.save()

    def _add_distributor(self):
        """
        Add a distributor with some standard settings.
        """
        repository = Repository.objects.get(name=TestRepository.NAME)
        distributor = RepositoryDistributor(repository=repository)
        distributor.name = 'Public'
        distributor.type = 'YUM'
        distributor.auto_publish = True
        distributor.save()

    def setUp(self):
        self._create_repository()

    def tearDown(self):
        self._delete_repository()

    def test_add_importer(self):
        self._add_importer()

    def test_add_distributor(self):
        self._add_distributor()

    def test_inspect_repository(self):
        """
        Inspect a repository.
        """
        repository = Repository.objects.get(name=TestRepository.NAME)

        # Read notes and scratchpad
        self.assertEqual(repository.notes.mapping['organization'], 'Engineering')
        self.assertEqual(repository.scratchpad.mapping['hello'], 'world')
        self.assertEqual(repository.scratchpad.mapping.get('xx', 'good'), 'good')

        # This is what happens when a key is not in the notes and [] is used.
        with self.assertRaises(KeyError):
            _ = repository.notes.mapping['xx']

    def test_inspect_importer(self):
        self._add_importer()
        repository = Repository.objects.get(name=TestRepository.NAME)
        importer = repository.importers.first()

        self.assertEqual(importer.feed_url, 'http://content-world/everyting/')

        # SSL
        self.assertTrue(importer.ssl_validation)
        self.assertEqual(importer.ssl_ca_certificate, 'MY-CA')
        self.assertEqual(importer.ssl_client_certificate, 'MY-CERTIFICATE')
        self.assertEqual(importer.ssl_client_key, 'MY-KEY')

        # Basic auth settings
        self.assertEqual(importer.basic_auth_user, 'Elmer')
        self.assertEqual(importer.basic_auth_password, 'Fudd')

    def test_update_note(self):
        """
        Update the notes.
        """
        repository = Repository.objects.get(name=TestRepository.NAME)
        repository.notes.mapping['name'] = 'Elvis'
        repository.notes.mapping.update({'age': 98})

        repository = Repository.objects.get(name=TestRepository.NAME)
        self.assertEqual(repository.notes.mapping['name'], 'Elvis')
        self.assertEqual(repository.notes.mapping['age'], '98')
