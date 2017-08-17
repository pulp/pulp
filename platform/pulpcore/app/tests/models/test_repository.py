
from django.test import TestCase

from pulpcore.app.models import Repository, Importer, Publisher, FileContent


class TestRepository(TestCase):

    def test_natural_key(self):
        repository = Repository(name='test')
        self.assertEqual(repository.natural_key(), (repository.name,))


class RepositoryExample(TestCase):

    NAME = 'zoo'

    def create_repository(self):
        """
        Create a repository with sample notes.
        """
        repository = Repository(name=RepositoryExample.NAME)
        repository.notes.mapping['organization'] = 'Engineering'
        repository.notes.mapping.update({'age': 10})
        repository.save()

    def delete_repository(self):
        """
        Delete the repository.
        """
        repository = Repository.objects.filter(name=RepositoryExample.NAME)
        repository.delete()

    def add_importer(self):
        """
        Add an importer with feed URL and some standard settings.
        """
        ca = 'MY-CA'
        certificate = 'MY-CERTIFICATE'
        key = 'MY-KEY'
        repository = Repository.objects.get(name=RepositoryExample.NAME)
        importer = Importer(repository=repository)
        importer.name = 'Upstream'
        importer.feed_url = 'http://content-world/everyting/'
        importer.ssl_validation = True
        importer.ssl_ca_certificate = FileContent(ca)
        importer.ssl_client_certificate = FileContent(certificate)
        importer.ssl_client_key = FileContent(key)
        importer.proxy_url = 'http://elmer:fudd@warnerbrothers.com'
        importer.basic_auth_user = 'Elmer'
        importer.basic_auth_password = 'Fudd'
        importer.save()

    def add_publishers(self):
        """
        Add a publisher with some standard settings.
        """
        repository = Repository.objects.get(name=RepositoryExample.NAME)
        for n in range(3):
            publisher = Publisher(repository=repository)
            publisher.name = 'p{}'.format(n)
            publisher.auto_publish = True
            publisher.save()

    def setUp(self):
        self.create_repository()

    def tearDown(self):
        self.delete_repository()

    def test_add_importer(self):
        self.add_importer()

    def test_add_publisher(self):
        self.add_publishers()

    def test_inspect_repository(self):
        """
        Inspect a repository.
        """
        repository = Repository.objects.get(name=RepositoryExample.NAME)

        # Read notes
        self.assertEqual(repository.notes.mapping['organization'], 'Engineering')

        # This is what happens when a key is not in the notes and [] is used.
        with self.assertRaises(KeyError):
            repository.notes.mapping['xx']

    def test_inspect_importer(self):
        self.add_importer()
        repository = Repository.objects.get(name=RepositoryExample.NAME)
        importer = repository.importers.first()

        self.assertEqual(importer.feed_url, 'http://content-world/everyting/')

        # SSL
        self.assertTrue(importer.ssl_validation)
        # Lousy test that leaks files but fine for initial sanity testing.
        self.assertEqual(
            open(str(importer.ssl_ca_certificate)).read(),
            'MY-CA')
        self.assertEqual(
            open(str(importer.ssl_client_certificate)).read(),
            'MY-CERTIFICATE')
        self.assertEqual(
            open(str(importer.ssl_client_key)).read(),
            'MY-KEY')

        # Basic auth settings
        self.assertEqual(importer.basic_auth_user, 'Elmer')
        self.assertEqual(importer.basic_auth_password, 'Fudd')

    def test_update_note(self):
        """
        Update the notes.
        """
        repository = Repository.objects.get(name=RepositoryExample.NAME)
        repository.notes.mapping['name'] = 'Elvis'
        repository.notes.mapping.update({'age': 98})

        repository = Repository.objects.get(name=RepositoryExample.NAME)
        self.assertEqual(repository.notes.mapping['name'], 'Elvis')
        self.assertEqual(repository.notes.mapping['age'], '98')
