import hashlib
import os
import tempfile
import shutil

from django.conf import settings
from django.db import models
from django.test import TestCase
from django.core.files import File

from pulpcore.app.models import Repository, RepositoryContent, Content, Artifact


NAME = 'test'
TYPE = 'test'


class ContentExample(TestCase):

    REPO_NAME = 'test'

    def setUp(self):
        settings.MEDIA_ROOT = tempfile.mkdtemp(prefix='pulp-')
        self.repository = self.add_repository()
        self.content = self.add_content()

    def tearDown(self):
        shutil.rmtree(settings.MEDIA_ROOT)

    def add_repository(self):
        repository = Repository(name=NAME)
        repository.save()
        return repository

    def associate(self):
        association = RepositoryContent(repository=self.repository, content=self.content)
        association.save()

    def add_content(self):
        content = Content(type=TYPE)
        content.save()
        return content

    def publish(self, artifact):
        """
        Fake publish.
        The artifact.relative_path will be the file relative path.
            Example: "3/test_content.py"
        The artifact.file.name will be the absolute path to where it is stored.
            Example: "/tmp/pulp-viCVvC/units/test/e3/b0c4429b93855/9/test_content.py"
        """
        self.assertEqual(os.path.basename(artifact.relative_path), os.path.basename(__file__))
        self.assertEqual(os.path.basename(artifact.file.name), os.path.basename(__file__))

    def add_artifacts(self):
        """
        Example of an importer adding files.  Using __file__, let pretend we have
        downloaded __file__ and want to add it to the content unit.  To make the
        files unique and to simulate file with meaningful relative paths, let's
        prefix the {n}/ directory to the file name.
        """
        paths = []
        for n in range(10):
            artifact = Artifact(content=self.content)
            # Set the artifact name as n/<name> to make them unique.
            artifact.relative_path = '{0}/{1}'.format(n, os.path.basename(__file__))
            # Set the file content (to be stored).
            with open(__file__) as fp:
                artifact.file = File(fp)
            artifact.save()
            paths.append(artifact.file.name)
        return paths

    def test_publishing(self):
        """
        Example of publishing.
        for each content unit, we'll iterate all of the artifacts (files) and publish them.
        The artifact.relative_path already contains relative path information needed for
        publishing which makes this easy.
        """
        self.add_artifacts()

        # publishing
        for artifact in self.content.artifacts.all():
            self.publish(artifact)

    def test_reading(self):
        self.add_artifacts()

        # reading
        for artifact in self.content.artifacts.all():
            artifact.file.open(mode='rb')
            with open(__file__, mode='rb') as fp:
                self.assertEqual(artifact.file.read(), fp.read())
            artifact.file.close()

    def test_find_artifacts_by_path(self):
        n = 0
        self.associate()
        paths = self.add_artifacts()
        for content in (c.cast() for c in self.repository.content.filter(type=TYPE)):
            for artifact in content.artifacts.filter(file=paths[0]):
                n += 1
        self.assertGreater(n, 0)

    def test_natural_key_digest(self):
        """Assert the basic functionality of Content.natural_key_digest."""
        class BoringContent(Content):
            my_field = models.TextField()
            natural_key_fields = (my_field,)

        content = BoringContent(my_field='wheat')
        expected_hash = hashlib.sha256()
        expected_hash.update('my_fieldwheat'.encode(encoding='utf-8'))

        digest = content.natural_key_digest()
        self.assertEqual(expected_hash.hexdigest(), digest)
