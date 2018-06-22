import mock
from unittest import TestCase

from pulpcore.app.models import Distribution
from pulpcore.app.serializers import (
    DistributionSerializer,
    RepositoryPublishURLSerializer,
)
from rest_framework import serializers


class TestRepositoryPublishURLSerializer(TestCase):

    @mock.patch('pulpcore.app.serializers.repository.models.RepositoryVersion')
    def test_validate_repository_only(self, mock_version):
        mock_repo = mock.MagicMock()
        data = {'repository': mock_repo}
        serializer = RepositoryPublishURLSerializer()
        new_data = serializer.validate(data)
        self.assertEqual(new_data, {'repository_version': mock_version.latest.return_value})
        mock_version.latest.assert_called_once_with(mock_repo)

    def test_validate_repository_version_only(self):
        mock_version = mock.MagicMock()
        data = {'repository_version': mock_version}
        serializer = RepositoryPublishURLSerializer()
        new_data = serializer.validate(data)
        self.assertEqual(new_data, {'repository_version': mock_version})

    def test_validate_repository_and_repository_version(self):
        mock_version = mock.MagicMock()
        mock_repository = mock.MagicMock()
        data = {'repository_version': mock_version, 'repository': mock_repository}
        serializer = RepositoryPublishURLSerializer()
        with self.assertRaises(serializers.ValidationError):
            serializer.validate(data)

    def test_validate_no_repository_no_version(self):
        serializer = RepositoryPublishURLSerializer()
        with self.assertRaises(serializers.ValidationError):
            serializer.validate({})

    @mock.patch('pulpcore.app.serializers.repository.models.RepositoryVersion')
    def test_validate_repository_only_unknown_field(self, mock_version):
        mock_repo = mock.MagicMock()
        data = {'repository': mock_repo, 'unknown_field': 'unknown'}
        serializer = RepositoryPublishURLSerializer(data=data)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate(data)

    def test_validate_repository_version_only_unknown_field(self):
        mock_version = mock.MagicMock()
        data = {'repository_version': mock_version, 'unknown_field': 'unknown'}
        serializer = RepositoryPublishURLSerializer(data=data)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate(data)


class TestDistributionPath(TestCase):
    def test_overlap(self):
        Distribution.objects.create(base_path="foo/bar", name="foobar")
        overlap_errors = {'base_path': ["Overlaps with existing distribution 'foobar'"]}

        # test that the new distribution cannot be nested in an existing path
        data = {"name": "foobarbaz", "base_path": "foo/bar/baz"}
        serializer = DistributionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(overlap_errors, serializer.errors)

        # test that the new distribution cannot nest an existing path
        data = {"name": "foo", "base_path": "foo"}
        serializer = DistributionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(overlap_errors, serializer.errors)

    def test_no_overlap(self):
        Distribution.objects.create(base_path="fu/bar", name="fubar")

        # different path
        data = {"name": "fufu", "base_path": "fubar"}
        serializer = DistributionSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertDictEqual({}, serializer.errors)

        # common base path but different path
        data = {"name": "fufu", "base_path": "fu/baz"}
        serializer = DistributionSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertDictEqual({}, serializer.errors)

    def test_slashes(self):
        overlap_errors = {'base_path': ["Relative path cannot begin or end with slashes."]}

        data = {"name": "fefe", "base_path": "fefe/"}
        serializer = DistributionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(overlap_errors, serializer.errors)

        data = {"name": "fefe", "base_path": "/fefe/foo"}
        serializer = DistributionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(overlap_errors, serializer.errors)

    def test_uniqueness(self):
        Distribution.objects.create(base_path="fizz/buzz", name="fizzbuzz")
        data = {"name": "feefee", "base_path": "fizz/buzz"}
        overlap_errors = {'base_path': ["This field must be unique."]}

        serializer = DistributionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(overlap_errors, serializer.errors)
