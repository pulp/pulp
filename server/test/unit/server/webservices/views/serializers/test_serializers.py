from bson.objectid import ObjectId
import mock

from pulp.common.compat import unittest
from pulp.server import exceptions
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
                remapped_fields = {'new thing': 'old thing'}

        test_serializer = TestSerializer(instance='qux',
                                         context={'apple': 'pear'},
                                         multiple=True)

        self.assertEquals(test_serializer.instance, 'qux')
        self.assertDictEqual(test_serializer.context, {'apple': 'pear'})
        self.assertEquals(test_serializer._exclude_fields, ['baz'])
        self.assertEquals(test_serializer._mask_fields, ['foo__bar'])
        self.assertDictEqual(test_serializer._remapped_fields, {'new thing': 'old thing'})
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
        self.assertEqual(serializers.ImporterSerializer.Meta.mask_fields,
                         ['config__basic_auth_password', 'config__proxy_password'])
        self.assertDictEqual(serializers.ImporterSerializer.Meta.remapped_fields, {'id': '_id'})

    @mock.patch('pulp.server.webservices.views.serializers.reverse')
    def test_get_href(self, m_reverse):
        instance = {
            'repo_id': 'apple',
            'importer_type_id': 'pear'
        }
        test_serializer = serializers.ImporterSerializer()
        result = test_serializer.get_href(instance)

        self.assertTrue(result is m_reverse.return_value)
        m_reverse.assert_called_once_with(
            'repo_importer_resource', kwargs={'repo_id': 'apple', 'importer_id': 'pear'})


@mock.patch('pulp.server.webservices.views.serializers.ModelSerializer._translate__id')
class TestTranslateFilters(unittest.TestCase):
    """
    Test the translation of arbitrary Mongo queries from external API representation to new
    internal database fields.
    """

    def setUp(self):
        """
        Creates and configures a model and serializer for all following tests.
        """

        class FakeSerializer(serializers.ModelSerializer):
            """Create a fake serialzer for the tests."""

            class Meta:
                """Defines how fields should be remapped."""
                remapped_fields = {'internal': 'external', 'id': '_id'}

            def translate_field(self, *args, **kwargs):
                """Overrides parent to test only the unit."""
                return 'translated'

        self.serializer = FakeSerializer()
        self.mock_doc = mock.MagicMock()
        self.mock_doc._fields = ['internal', 'do_not_change']
        self.trans_value = 'the key for this value should be translated'
        self.untrans_value = 'the key for this value should NOT have been translated'

    def test_simple_key_value(self, mock_trans_id):
        """Test translation of form `{key: value}`."""
        to_translate = {'external': self.trans_value, 'do_not_change': self.untrans_value}
        result = self.serializer.translate_filters(self.mock_doc, to_translate)
        self.assertTrue('translated' in result)
        self.assertTrue(result['translated'] is self.trans_value)
        self.assertTrue('do_not_change' in result)
        self.assertTrue(result['do_not_change'] is self.untrans_value)

    def test__id(self, mock_trans_id):
        """Test translation of form `{_id: value}`."""
        self._id_val = 'translate_me!'
        to_translate = {'_id': self._id_val}
        result = self.serializer.translate_filters(self.mock_doc, to_translate)
        self.assertDictEqual(result, {'_id': mock_trans_id.return_value})
        mock_trans_id.assert_called_once_with(self._id_val)

    def test__id_not_remapped(self, mock_trans_id):
        """Test translation of form `{_id: value}` when '_id' has not been remapped."""
        self.serializer._remapped_fields.pop('id')
        self._id_val = 'do not translate_me!'
        to_translate = {'_id': self._id_val}
        result = self.serializer.translate_filters(self.mock_doc, to_translate)
        self.assertDictEqual(result, to_translate)
        self.assertFalse(mock_trans_id.called)

    def test_query_value(self, mock_trans_id):
        """Test translation of form `{$key: value}`.

        Note: This is not a valid query on its own, but can a leaf of nested queries.
        """
        to_translate = {'$is': self.untrans_value}
        result = self.serializer.translate_filters(self.mock_doc, to_translate)
        self.assertDictEqual(to_translate, result)

    def test_list_of_items(self, mock_trans_id):
        """Test translation of form `{$key: [values]}`."""
        value_list = ['value_1', 'value_2']
        to_translate = {'$in': value_list}
        result = self.serializer.translate_filters(self.mock_doc, to_translate)
        self.assertTrue('$in' in result)
        self.assertEqual(result['$in'], value_list)

    def test_list_of_queries(self, mock_trans_id):
        """Test translation of form `{$key: [{query}, {query}]}`."""
        query_1 = {"external": self.trans_value}
        query_2 = {"do_not_change": self.untrans_value}
        to_translate = {'$and': [query_1, query_2]}
        result = self.serializer.translate_filters(self.mock_doc, to_translate)
        self.assertTrue('$and' in result)
        self.assertTrue(type(result['$and']) is list)
        self.assertTrue('translated' in result['$and'][0])
        self.assertTrue(result['$and'][0]['translated'] is self.trans_value)
        self.assertTrue('do_not_change' in result['$and'][1])
        self.assertTrue(result['$and'][1]['do_not_change'] is self.untrans_value)

    def test_nested_dict(self, mock_trans_id):
        """Test translation of form `{$key: {query}}`."""
        interior_dict = {'external': self.trans_value, 'do_not_change': self.untrans_value}
        to_translate = {'$elemMatch': interior_dict}
        result = self.serializer.translate_filters(self.mock_doc, to_translate)
        self.assertTrue('$elemMatch' in result)
        self.assertTrue(type(result['$elemMatch']) is dict)
        self.assertDictEqual({'translated': self.trans_value, 'do_not_change': self.untrans_value},
                             result['$elemMatch'])

    def test_nested_translated_dict(self, mock_trans_id):
        """Test translation of form `{key: {query}}`."""
        interior_dict = {'external': self.trans_value, 'do_not_change': self.untrans_value}
        to_translate = {'external': interior_dict}
        result = self.serializer.translate_filters(self.mock_doc, to_translate)
        self.assertTrue('translated' in result)
        self.assertTrue(type(result['translated']) is dict)
        self.assertDictEqual({'translated': self.trans_value, 'do_not_change': self.untrans_value},
                             result['translated'])

    def test_deep_nest(self, mock_trans_id):
        """Test translation of a deeply nested query."""
        interior_1 = {'external': self.trans_value, 'do_not_change': self.untrans_value}
        interior_2 = {'$in': ['a', 'b', 'c']}
        and_query = {'$and': [interior_1, interior_2]}
        to_translate = {'$elemMatch': and_query}
        result = self.serializer.translate_filters(self.mock_doc, to_translate)
        self.assertTrue('$elemMatch' in result)
        self.assertTrue(type(result['$elemMatch']) is dict)
        self.assertTrue('$and' in result['$elemMatch'])
        self.assertTrue(type(result['$elemMatch']['$and']) is list)
        self.assertDictEqual({'translated': self.trans_value, 'do_not_change': self.untrans_value},
                             result['$elemMatch']['$and'][0])
        self.assertDictEqual(result['$elemMatch']['$and'][1], interior_2)

    def test_deeper_nest(self, mock_trans_id):
        """Test translation of another deeply nested query."""
        interior_1 = {'external': self.trans_value, 'do_not_change': self.untrans_value}
        interior_2 = {'$in': ['a', 'b', 'c']}
        and_query = {'$and': [interior_1, interior_2]}
        to_translate = {'id': {'$elemMatch': and_query}}
        result = self.serializer.translate_filters(self.mock_doc, to_translate)
        self.assertTrue('$elemMatch' in result['id'])
        self.assertTrue(type(result['id']['$elemMatch']) is dict)
        self.assertTrue('$and' in result['id']['$elemMatch'])
        self.assertTrue(type(result['id']['$elemMatch']['$and']) is list)
        self.assertDictEqual({'translated': self.trans_value, 'do_not_change': self.untrans_value},
                             result['id']['$elemMatch']['$and'][0])
        self.assertDictEqual(result['id']['$elemMatch']['$and'][1], interior_2)


class TestModelSerializer(unittest.TestCase):

    def test_to_representation(self):
        """
        Ensure that internal db fields are changed to their external representation.
        """

        class FakeSerializer(serializers.ModelSerializer):

            class Meta:
                remapped_fields = {'internal': 'external'}

        mock_doc = mock.MagicMock()
        mock_doc._fields = ['internal', 'leave']
        mock_doc.internal = 'was internal'
        mock_doc.leave = 'should not change'
        test_serializer = FakeSerializer()
        result = test_serializer.to_representation(mock_doc)
        self.assertDictEqual(result, {'leave': 'should not change', 'external': 'was internal'})

    def test_transalte__id_str(self):
        """
        Test the translation of _id if the value is a string representation of an ObjectId.
        """

        class FakeSerializer(serializers.ModelSerializer):
            pass

        obj_id = ObjectId()
        test_serializer = FakeSerializer()
        result = test_serializer._translate__id(str(obj_id))
        self.assertEqual(result, obj_id)

    def test_translate__id_dict_with_str(self):
        """
        Test the translation of a query that uses a Mongo operator.
        """

        class FakeSerializer(serializers.ModelSerializer):
            pass

        obj_id = ObjectId()
        test_serializer = FakeSerializer()
        result = test_serializer._translate__id({'$mongo_operator': str(obj_id)})
        self.assertDictEqual(result, {'$mongo_operator': obj_id})

    def test_translate__id_dict_with_list(self):
        """
        Test the translation of a more complex _id field.
        """

        class FakeSerializer(serializers.ModelSerializer):
            pass

        obj_ids = [ObjectId() for i in range(3)]
        string_ids = [str(obj_id) for obj_id in obj_ids]
        test_serializer = FakeSerializer()
        result = test_serializer._translate__id({'$in': string_ids})
        self.assertDictEqual(result, {'$in': obj_ids})

    def test_tranlate__id_type_failure(self):
        """
        Raise if _id is a type that we cannot translate.
        """

        class FakeSerializer(serializers.ModelSerializer):
            pass

        test_serializer = FakeSerializer()
        self.assertRaises(exceptions.InvalidValue, test_serializer._translate__id, ['invalid'])

    def test_tranlate__id_nested_type_failure(self):
        """
        Raise if _id is structured in a way that we cannot translate.
        """

        class FakeSerializer(serializers.ModelSerializer):
            pass

        search_term = {'$and': {'implementation': 'doesnt support this'}}
        test_serializer = FakeSerializer()
        self.assertRaises(exceptions.InvalidValue, test_serializer._translate__id, search_term)

    def test_translate_field(self):
        """
        Test that individual strings are translated correctly from external to internal repr.
        """

        class FakeSerializer(serializers.ModelSerializer):

            class Meta:
                remapped_fields = {'internal': 'external'}

        mock_model = mock.MagicMock()
        mock_model.internal.db_field = 'internal_db'
        test_serializer = FakeSerializer()
        result = test_serializer.translate_field(mock_model, 'external')
        self.assertEqual(result, 'internal_db')

    def test_translate_field_reverse(self):
        """
        Test that individual strings are translated correctly from external to internal repr.
        """

        class FakeSerializer(serializers.ModelSerializer):

            class Meta:
                remapped_fields = {'internal': 'external'}

        mock_model = mock.MagicMock()
        mock_model.internal.db_field = 'internal_db'
        test_serializer = FakeSerializer()
        result = test_serializer.translate_field_reverse('internal')
        self.assertEqual(result, 'external')

    @mock.patch('pulp.server.db.model.criteria.Criteria.from_dict')
    @mock.patch('pulp.server.webservices.views.serializers.ModelSerializer.translate_field')
    @mock.patch('pulp.server.webservices.views.serializers.ModelSerializer.translate_filters')
    def test_translate_criteria(self, mock_translate_filters, mock_translate, mock_new_crit):
        """
        Test that each fo the fields of criteria are translated appropriately.
        """
        test_serializer = serializers.ModelSerializer()
        mock_model = mock.MagicMock()
        mock_crit = mock.MagicMock()
        mock_crit.fields = ['f1', 'f2']
        mock_crit.sort = [('field', 'dir')]
        mock_crit.as_dict.return_value = {}
        result = test_serializer.translate_criteria(mock_model, mock_crit)
        self.assertTrue(result is mock_new_crit.return_value)
        expected_crit_dict = {'filters': mock_translate_filters.return_value,
                              'sort': [(mock_translate.return_value, 'dir')],
                              'fields': [mock_translate.return_value, mock_translate.return_value]}
        mock_translate.assert_has_calls(
            [mock.call(mock_model, 'field'), mock.call(mock_model, 'f1'),
             mock.call(mock_model, 'f2')])
        mock_new_crit.assert_called_once_with(expected_crit_dict)

    def test_translate_nonexistent_field(self):
        """
        Test that attempting to translate nonexistent fields raises the correct exception
        """

        class FakeSerializer(serializers.ModelSerializer):
            pass

        mock_model = mock.MagicMock()
        # 'del' the field attribute so the mock throws the required AttributeError on access
        del(mock_model.nonexistent_field)
        test_serializer = FakeSerializer()
        self.assertRaises(exceptions.InvalidValue, test_serializer.translate_field,
                          mock_model, 'nonexistent_field')


class TestRepository(unittest.TestCase):
    """
    Tests for the repository serializer.
    """

    def test_meta(self):
        """
        Make sure that scratchpad is excluded.
        """
        self.assertEquals(serializers.Repository.Meta.exclude_fields, [])
        self.assertDictEqual(serializers.Repository.Meta.remapped_fields,
                             {'repo_id': 'id', 'id': '_id'})

    @mock.patch('pulp.server.webservices.views.serializers.reverse')
    def test_get_href(self, mock_rev):
        """
        Test the generation of a href for a repository.
        """
        repo = mock.MagicMock()
        test_serializer = serializers.Repository()
        result = test_serializer.get_href(repo)
        self.assertEquals(result, mock_rev.return_value)
        mock_rev.assert_called_once_with('repo_resource', kwargs={'repo_id': repo.repo_id})

    def test_to_representation(self):
        """
        This is not really necessary, but this test ensures that the ModelSerializer works
        as expected with a repository object. Though this is not a true unit test, I felt that
        it was crucial enough to warrant a little extra testing here.

        Specifically, make sure that repo_id in the database is converted to id for backwards
        compatability and _id refers to what used to be stored in id.
        """
        repo = mock.MagicMock()
        repo._fields = ['best', 'still_good', 'id', 'repo_id']
        repo.best = 'joule'
        repo.id = 'test_id'
        repo.repo_id = 'test_repo_id'
        repo.still_good = 'morning_times'
        test_serializer = serializers.Repository()
        result = test_serializer.to_representation(repo)
        self.assertDictEqual(result, {'best': 'joule', 'still_good': 'morning_times',
                                      '_id': 'test_id', 'id': 'test_repo_id'})


class TestDistributor(unittest.TestCase):

    def test_meta(self):
        self.assertDictEqual(serializers.Distributor.Meta.remapped_fields,
                             {'distributor_id': 'id', 'id': '_id'})

    @mock.patch('pulp.server.webservices.views.serializers.reverse')
    def test_get_href(self, m_reverse):
        instance = {
            'repo_id': 'apple',
            'distributor_id': 'pear'
        }
        test_serializer = serializers.Distributor()
        result = test_serializer.get_href(instance)

        self.assertTrue(result is m_reverse.return_value)
        m_reverse.assert_called_once_with(
            'repo_distributor_resource', kwargs={'repo_id': 'apple', 'distributor_id': 'pear'})


class TestUser(unittest.TestCase):
    """
    Tests for the user serializer.
    """

    def test_meta(self):
        """
        Make sure that password is excluded and `id` is displayed as `_id`.
        """
        self.assertEquals(serializers.User.Meta.exclude_fields, ['password'])
        self.assertDictEqual(serializers.User.Meta.remapped_fields, {'id': '_id'})

    @mock.patch('pulp.server.webservices.views.serializers.reverse')
    def test_get_href(self, mock_rev):
        """
        Test that reverse is correctly called to create an href for the user.
        """
        user = mock.MagicMock()
        test_serializer = serializers.User()
        result = test_serializer.get_href(user)
        self.assertEquals(result, mock_rev.return_value)
        mock_rev.assert_called_once_with('user_resource', kwargs={'login': user.login})
