try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock

from pulp.server.webservices.views import serializers


class TestBaseSerializer(unittest.TestCase):

    def test_init_all_options(self):
        """
        test with everything possible specified at init
        """

        class TestSerializer(serializers.BaseSerializer):
            class Meta:
                mask_fields = ['foo__bar']
                exclude_fields = ['baz']

        test_serializer = TestSerializer(instance='qux',
                                         context={'apple': 'pear'},
                                         multiple=True)

        self.assertEquals(test_serializer.instance, 'qux')
        self.assertDictEqual(test_serializer.context, {'apple': 'pear'})
        self.assertEquals(test_serializer._exclude_fields, ['baz'])
        self.assertEquals(test_serializer._mask_fields, ['foo__bar'])
        self.assertEquals(test_serializer._multiple, True)

    def test_init_minimal(self):
        """
        test with minimal possible specified at init
        """

        class TestSerializer(serializers.BaseSerializer):
            pass

        test_serializer = TestSerializer(instance='qux')

        self.assertEquals(test_serializer.instance, 'qux')
        self.assertIsNone(test_serializer.context)
        self.assertEquals(test_serializer._exclude_fields, [])
        self.assertEquals(test_serializer._mask_fields, [])
        self.assertEquals(test_serializer._multiple, False)

    def test_to_representation(self):
        """
        Check that to_representation raises a NotImplementedError
        """
        test_serializer = serializers.BaseSerializer()
        self.assertRaises(NotImplementedError, test_serializer.to_representation, 'foo')

    def test_get_href(self):
        """
        Check that get_href returns None by default
        """
        test_serializer = serializers.BaseSerializer()
        self.assertRaises(NotImplementedError, test_serializer.get_href('foo'))

    @mock.patch('pulp.server.webservices.views.serializers.BaseSerializer._remove_excluded')
    @mock.patch('pulp.server.webservices.views.serializers.BaseSerializer._mask_field')
    def test__to_represenation_maxnimal(self, m_mask_field, m_remove_excluded):
        """
        Test _to_representation, with all possible options
        """
        representation = {'fake': 'instance'}

        class TestSerializer(serializers.BaseSerializer):
            class Meta:
                mask_fields = ['foo__bar']
                exclude_fields = ['baz__quux']

            def get_href(self, instance):
                return 'apples'

            def to_representation(self, instance):
                return representation

        test_serializer = TestSerializer('pears')
        results = test_serializer._to_representation('pears')

        self.assertDictEqual(results, {'fake': 'instance', '_href': 'apples'})
        m_mask_field.assert_called_once_with(['foo', 'bar'], representation)
        m_remove_excluded.assert_called_once_with(['baz', 'quux'], representation)

    def test__to_represenation_minimal(self):
        """
        Test _to_representation, with all possible options
        """
        representation = {'fake': 'instance'}

        class TestSerializer(serializers.BaseSerializer):

            def to_representation(self, instance):
                return representation

        test_serializer = TestSerializer('pears')
        results = test_serializer._to_representation('pears')

        self.assertDictEqual(results, {'fake': 'instance'})

    def test__remove_excluded(self):
        """
        Test with a single accessor
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': 'quux'}
        serializer._remove_excluded(['baz'], representation)
        self.assertDictEqual(representation, {'foo': 'bar'})

    def test__remove_excluded_missing_field(self):
        """
        Test with a single accessor
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar'}
        serializer._remove_excluded(['baz'], representation)
        self.assertDictEqual(representation, {'foo': 'bar'})

    def test__remove_excluded_multiple(self):
        """
        Test with multiple accessors
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': {'quux': 'apples'}}
        serializer._remove_excluded(['baz', 'quux'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': {}})

    def test__remove_excluded_multiple_missing_field(self):
        """
        Test with multiple accessors
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar'}
        serializer._remove_excluded(['baz', 'quux'], representation)
        self.assertDictEqual(representation, {'foo': 'bar'})

    def test__remove_excluded_multiple_missing_inner_field(self):
        """
        Test with multiple accessors
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': {}}
        serializer._remove_excluded(['baz', 'quux'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': {}})

    def test__remove_excluded_multiple_value_none(self):
        """
        Test with multiple accessors
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': None}
        serializer._remove_excluded(['baz', 'quux'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': None})

    def test__mask_field(self):
        """
        Test with a single accessor
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': 'quux'}
        serializer._mask_field(['baz'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': '*****'})

    def test__mask_none_value(self):
        """
        Test with a single accessor
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': None}
        serializer._mask_field(['baz'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': None})

    def test__mask_missing_field(self):
        """
        Test with a single accessor
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar'}
        serializer._mask_field(['baz'], representation)
        self.assertDictEqual(representation, {'foo': 'bar'})

    def test__mask_field_multiple(self):
        """
        Test field masking with a multiple accessors
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': {'quux': 'apples'}}
        serializer._mask_field(['baz', 'quux'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': {'quux': '*****'}})

    def test__mask_field_multiple_missing_field(self):
        """
        Test field masking with a multiple accessors
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar'}
        serializer._mask_field(['baz', 'quux'], representation)
        self.assertDictEqual(representation, {'foo': 'bar'})

    def test__mask_field_multiple_missing_inner_field(self):
        """
        Test field masking with a multiple accessors
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': {}}
        serializer._mask_field(['baz', 'quux'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': {}})

    def test__mask_field_multiple_value_none(self):
        """
        Test field masking with a multiple accessors
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': None}
        serializer._mask_field(['baz', 'quux'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': None})

    def test_data_multiple(self):
        class TestSerializer(serializers.BaseSerializer):
            def to_representation(self, instance):
                return {'key': instance}

        serializer = TestSerializer(['apple', 'pear'], multiple=True)

        results = serializer.data

        expected_results = [{'key': 'apple'}, {'key': 'pear'}]
        self.assertEquals(list(results), expected_results)

    def test_data_single(self):
        class TestSerializer(serializers.BaseSerializer):
            def to_representation(self, instance):
                return {'key': instance}

        serializer = TestSerializer('pear', multiple=False)

        results = serializer.data

        expected_results = {'key': 'pear'}
        self.assertEquals(results, expected_results)


class TestDictSerializer(unittest.TestCase):

    def test_to_representation(self):
        instance_value = {'apple': 'pear'}
        test_serializer = serializers.DictSerializer()

        result = test_serializer.to_representation(instance_value)

        # Ensure that the original value was copied and not referenced exactly
        self.assertFalse(instance_value is result)

        self.assertDictEqual(instance_value, result)


class TestImporterSerializer(unittest.TestCase):

    def test_meta(self):
        self.assertEquals(serializers.ImporterSerializer.Meta.mask_fields,
                          ['config__basic_auth_password', 'config__proxy_password'])

    @mock.patch('pulp.server.webservices.views.serializers.reverse')
    def test_get_href(self, m_reverse):
        m_reverse.return_value = 'kiwi'
        instance = {
            'repo_id': 'apple',
            'id': 'pear'
        }
        test_serializer = serializers.ImporterSerializer()
        result = test_serializer.get_href(instance)

        self.assertEquals(result, 'kiwi')
        m_reverse.assert_called_once_with('repo_importer_resource',
                                          kwargs={'repo_id': 'apple',
                                                  'importer_id': 'pear'})
