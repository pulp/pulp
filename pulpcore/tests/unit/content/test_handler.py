from unittest.mock import Mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from pulpcore.content import Handler
from pulpcore.plugin.models import Artifact, ContentArtifact

from pulp_file.app.models import FileContent


class HandlerSaveContentTestCase(TestCase):

    def setUp(self):
        self.f1 = FileContent.objects.create(relative_path='f1', digest='1')
        self.f1.artifact = None
        self.f2 = FileContent.objects.create(relative_path='f2', digest='1')
        self.f2.artifact = None

    def download_result_mock(self, path):
        dr = Mock()
        dr.artifact_attributes = {'size': 0}
        for digest_type in Artifact.DIGEST_FIELDS:
            dr.artifact_attributes[digest_type] = '1'
        dr.path = SimpleUploadedFile(name=path, content='')
        return dr

    def test_save_content_artifact(self):
        """Artifact needs to be created."""
        cch = Handler()
        new_artifact = cch._save_content_artifact(self.download_result_mock('f1'),
                                                  ContentArtifact.objects.get(pk=self.f1.pk))
        f1 = FileContent.objects.get(pk=self.f1.pk)
        self.assertIsNotNone(new_artifact)
        self.assertEqual(f1._artifacts.get().pk, new_artifact.pk)

    def test_save_content_artifact_artifact_already_exists(self):
        """Artifact turns out to already exist."""
        cch = Handler()
        new_artifact = cch._save_content_artifact(self.download_result_mock('f1'),
                                                  ContentArtifact.objects.get(pk=self.f1.pk))

        existing_artifact = cch._save_content_artifact(self.download_result_mock('f2'),
                                                       ContentArtifact.objects.get(pk=self.f2.pk))
        f2 = FileContent.objects.get(pk=self.f2.pk)
        self.assertEqual(existing_artifact.pk, new_artifact.pk)
        self.assertEqual(f2._artifacts.get().pk, existing_artifact.pk)
