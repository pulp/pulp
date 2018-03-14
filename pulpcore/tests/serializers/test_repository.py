from unittest import TestCase

from pulpcore.app.models import Distribution
from pulpcore.app.serializers import DistributionSerializer


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
