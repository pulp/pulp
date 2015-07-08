import mock

from pulp.common.compat import unittest
# The serializers module should not normally be an starting point for imports, so we need to import
# the criteria module before serializers to prevent a circular import. This is only an issue when
# running this test module by itself, and will be fixed when pulp.server.db.model becomes a true
# module or moves to pulp.server.db.models. See https://pulp.plan.io/issues/1066
from pulp.server.db.model import criteria  # noqa
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

    def test__remove_excluded_multiple(self):
        """
        Test with multiple accessors
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': {'quux': 'apples'}}
        serializer._remove_excluded(['baz', 'quux'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': {}})

    def test__mask_field(self):
        """
        Test with a single accessor
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': 'quux'}
        serializer._mask_field(['baz'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': '*****'})

    def test__mask_field_multiple(self):
        """
        Test field masking with a multiple accessors
        """
        serializer = serializers.BaseSerializer('foo')
        representation = {'foo': 'bar', 'baz': {'quux': 'apples'}}
        serializer._mask_field(['baz', 'quux'], representation)
        self.assertDictEqual(representation, {'foo': 'bar', 'baz': {'quux': '*****'}})

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

    def test_translate_filters(self):
        """
        Translate criteria objects' filters to from external to internal representation for search.
        """

        class FakeSerializer(serializers.ModelSerializer):

            class Meta:
                remapped_fields = {'internal': 'external'}

        mock_model = mock.MagicMock()
        mock_model.internal.db_field = 'internal_db'
        filters = {'external': 'was external', 'leave': 'should not change'}
        test_serializer = FakeSerializer()
        result = test_serializer._translate_filters(mock_model, filters)
        self.assertDictEqual(result, {'internal_db': 'was external', 'leave': 'should not change'})

    def test_translate(self):
        """
        Test that individual strings are translated correctly from external to internal repr.
        """

        class FakeSerializer(serializers.ModelSerializer):

            class Meta:
                remapped_fields = {'internal': 'external'}

        mock_model = mock.MagicMock()
        mock_model.internal.db_field = 'internal_db'
        test_serializer = FakeSerializer()
        result = test_serializer._translate(mock_model, 'external')
        self.assertEqual(result, 'internal_db')

    @mock.patch('pulp.server.webservices.views.serializers.criteria.Criteria.from_dict')
    @mock.patch('pulp.server.webservices.views.serializers.ModelSerializer._translate')
    @mock.patch('pulp.server.webservices.views.serializers.ModelSerializer._translate_filters')
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
