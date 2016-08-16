"""
Test the pulp.server.db.model.criteria module.
"""

import copy
import re
import unittest

from datetime import datetime

from mock import patch

from pulp.server import exceptions
from pulp.server.db.model import criteria


FIELDS = set(('sort', 'skip', 'limit', 'filters', 'fields'))
ASSOCIATION_FIELDS = set(('type_ids', 'association_filters', 'unit_filters', 'association_sort',
                          'unit_sort', 'limit', 'skip', 'association_fields', 'unit_fields',
                          'remove_duplicates'))


class TestCriteria(unittest.TestCase):

    @patch.object(criteria.DateOperator, 'apply')
    def test_from_client_input_applies_date_operator(self, _apply):
        filters = {
            'created': {
                '$gt': {'$date': '2013-12-01T14:35:00Z'}
            }
        }
        query = {'filters': filters}
        criteria.Criteria.from_client_input(query)
        _apply.assert_called_once_with(filters)


class TestAsDict(unittest.TestCase):
    def test_empty(self):
        c = criteria.Criteria()
        ret = c.as_dict()
        self.assertTrue(isinstance(ret, dict))
        for field in FIELDS:
            self.assertTrue(ret[field] is None)

    def test_full(self):
        c = criteria.Criteria(
            filters={'name': {'$in': ['a', 'b']}},
            sort=(('name', 'ascending'),),
            limit=10,
            skip=10,
            fields=('name', 'id')
        )
        ret = c.as_dict()
        self.assertTrue(isinstance(ret['filters'], dict))
        self.assertEqual(ret['limit'], 10)
        self.assertEqual(ret['skip'], 10)
        self.assertEqual(ret['fields'], c.fields)
        self.assertEqual(set(ret.keys()), FIELDS)


class TestClientInputValidation(unittest.TestCase):
    def test_as_dict(self):
        # this should work
        criteria.Criteria.from_client_input({})

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria.Criteria.from_client_input, 'abc 123')

    def test_as_int(self):
        self.assertRaises(exceptions.InvalidValue, criteria.Criteria.from_client_input, 123)

    def test_as_none(self):
        self.assertRaises(exceptions.InvalidValue, criteria.Criteria.from_client_input, None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria.Criteria.from_client_input, True)

    def test_as_list(self):
        self.assertRaises(exceptions.InvalidValue, criteria.Criteria.from_client_input, [])


class TestFromDict(unittest.TestCase):
    """
    Test the Criteria.from_dict() method.
    """
    def test_from_dict(self):
        filters = {'some': 'filters'}
        sort = ['sort_item']
        limit = 42
        skip = 64
        fields = ['a_field']
        a_dict = {'filters': filters, 'sort': sort, 'limit': limit, 'skip': skip, 'fields': fields}

        new_criteria = criteria.Criteria.from_dict(a_dict)

        self.assertTrue(isinstance(new_criteria, criteria.Criteria))
        self.assertEqual(new_criteria.filters, filters)
        self.assertEqual(new_criteria.sort, sort)
        self.assertEqual(new_criteria.limit, limit)
        self.assertEqual(new_criteria.skip, skip)
        self.assertEqual(new_criteria.fields, fields)

    def test_from_dict_accepts_as_dict_as_input(self):
        """
        Verify that from_dict() accepts the output of as_dict() as input.
        """
        filters = {'some': 'filters'}
        sort = ['sort_item']
        limit = 42
        skip = 64
        fields = ['a_field']
        criteria_1 = criteria.Criteria(filters, sort, limit, skip, fields)

        criteria_2 = criteria.Criteria.from_dict(criteria_1.as_dict())

        self.assertTrue(isinstance(criteria_2, criteria.Criteria))
        self.assertEqual(criteria_2.filters, criteria_1.filters)
        self.assertEqual(criteria_2.sort, criteria_1.sort)
        self.assertEqual(criteria_2.limit, criteria_1.limit)
        self.assertEqual(criteria_2.skip, criteria_1.skip)
        self.assertEqual(criteria_2.fields, criteria_1.fields)


class TestValidateFilters(unittest.TestCase):
    def test_as_dict(self):
        input = {'id': 'repo1'}
        ret = criteria._validate_filters(input)
        self.assertEqual(ret, input)

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_filters, 'abc 123')

    def test_as_int(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_filters, 123)

    def test_as_none(self):
        ret = criteria._validate_filters(None)
        self.assertTrue(ret is None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_filters, True)

    def test_as_list(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_filters, [])


class TestValidateSort(unittest.TestCase):
    def test_as_list(self):
        input = []
        ret = criteria._validate_sort(input)
        self.assertEqual(ret, input)

    def test_as_tuple(self):
        input = ()
        ret = criteria._validate_sort(input)
        self.assertEqual(ret, [])

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_sort, 'abc 123')

    def test_as_int(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_sort, 123)

    def test_as_none(self):
        ret = criteria._validate_sort(None)
        self.assertTrue(ret is None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_sort, True)

    def test_as_dict(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_sort, {})


class TestValidateLimit(unittest.TestCase):
    def test_as_int(self):
        input = 20
        ret = criteria._validate_limit(input)
        self.assertEqual(ret, input)

    def test_as_int_string(self):
        input = '20'
        ret = criteria._validate_limit(input)
        self.assertEqual(ret, 20)

    def test_as_zero(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, 0)

    def test_as_negative(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, -1)

    def test_as_tuple(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, ())

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, 'abc 123')

    def test_as_list(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, [])

    def test_as_none(self):
        ret = criteria._validate_limit(None)
        self.assertTrue(ret is None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, True)

    def test_as_dict(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_limit, {})


class TestValidateSkip(unittest.TestCase):
    def test_as_int(self):
        input = 20
        ret = criteria._validate_skip(input)
        self.assertEqual(ret, input)

    def test_as_int_string(self):
        input = '20'
        ret = criteria._validate_skip(input)
        self.assertEqual(ret, 20)

    def test_as_zero(self):
        input = 0
        ret = criteria._validate_skip(input)
        self.assertEqual(ret, input)

    def test_as_negative(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip, -1)

    def test_as_tuple(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip, ())

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip, 'abc 123')

    def test_as_list(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip, [])

    def test_as_none(self):
        ret = criteria._validate_skip(None)
        self.assertTrue(ret is None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip, True)

    def test_as_dict(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_skip, {})


class TestValidateFields(unittest.TestCase):
    def test_as_list(self):
        input = []
        ret = criteria._validate_fields(input)
        self.assertEqual(ret, input)

    def test_as_tuple(self):
        input = ()
        ret = criteria._validate_fields(input)
        self.assertEqual(ret, list(input))

    def test_as_string(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields, 'abc 123')

    def test_as_int(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields, 123)

    def test_as_none(self):
        ret = criteria._validate_fields(None)
        self.assertTrue(ret is None)

    def test_as_bool(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields, True)

    def test_as_dict(self):
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields, {})

    def test_items_as_string(self):
        input = ['id', 'name']
        ret = criteria._validate_fields(input)
        self.assertEqual(ret, input)

    def test_items_as_int(self):
        input = ['id', 3]
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields, input)

    def test_items_as_dict(self):
        input = ['id', {}]
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields, input)

    def test_items_as_list(self):
        input = ['id', []]
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields, input)

    def test_items_as_bool(self):
        input = ['id', True]
        self.assertRaises(exceptions.InvalidValue, criteria._validate_fields, input)


class TestConvertionsForNot(unittest.TestCase):
    """
    Test that regular expressions for the Mongo operator `$not` are converted to a proper format.
    """
    def test__compile_regexs_for_not(self):
        """
        Test that regular expression is compiled to a regex object.
        """
        some_filter = {'key': {'$not': '^regexp?$'}}
        criteria._compile_regexs_for_not(some_filter)
        re_type = type(re.compile(''))
        self.assertTrue(isinstance(some_filter['key']['$not'], re_type))

    def test__compile_regexs_for_not_noop(self):
        """
        Test that _compile_regexs_for_not does nothing to the filter if there is no `$not` operator.
        """
        some_filter = {'key': {'$eq': 'value'}}
        expected_filter = copy.deepcopy(some_filter)
        criteria._compile_regexs_for_not(some_filter)
        self.assertEqual(some_filter, expected_filter)

    def test__get_patterns_for_not(self):
        """
        Test that a pattern is obtained from the regex object.
        """
        regex = '^regexp?$'
        some_filter = {'key': {'$not': re.compile(regex)}}
        filter_copy = criteria._get_patterns_for_not(some_filter)
        self.assertEqual(filter_copy['key']['$not'], regex)

    def test__get_patterns_for_not_noop(self):
        """
        Test that _get_patterns_for_not does nothing to the filter if there is no `$not` operator.
        """
        some_filter = {'key': {'$eq': 'value'}}
        filter_copy = criteria._get_patterns_for_not(some_filter)
        self.assertEqual(some_filter, filter_copy)


class TestDateOperator(unittest.TestCase):

    def test_apply(self):
        query = {
            'created': {
                '$gt': {'$date': '2013-12-01T14:35:00Z'}
            }
        }
        criteria.DateOperator.apply(query)
        self.assertTrue(isinstance(query['created']['$gt'], datetime))

    def test_translate(self):
        value = {'$date': '2013-12-01T14:35:00Z'}
        matched, translated = criteria.DateOperator.translate(value)
        self.assertTrue(matched)
        self.assertTrue(isinstance(translated, datetime))

    def test_translate_key_not_matched(self):
        value = {'$dated': '2013-12-01T14:35:00Z'}
        matched, translated = criteria.DateOperator.translate(value)
        self.assertFalse(matched)
        self.assertEqual(translated, value)

    def test_translate_dict_not_matched(self):
        value = {'$dated': '2013-12-01T14:35:00Z', 'unexpected': 1}
        matched, translated = criteria.DateOperator.translate(value)
        self.assertFalse(matched)
        self.assertEqual(translated, value)


class TestUnitAssociationCriteria(unittest.TestCase):

    def test_to_dict(self):
        c = criteria.UnitAssociationCriteria(
            type_ids=['rpm'],
            association_filters={},
            unit_filters={'name': 'test', '$not': re.compile('regexp?')},
            association_sort=None,
            unit_sort=None,
            limit=10,
            skip=10,
            association_fields=None,
            unit_fields=['foo', 'bar'],
            remove_duplicates=False
        )
        ret = c.to_dict()
        expected_unit_filters = {'name': 'test', '$not': 'regexp?'}
        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['association_filters'], dict))
        self.assertEqual(ret['limit'], 10)
        self.assertEqual(ret['skip'], 10)
        self.assertEqual(ret['unit_fields'], c.unit_fields)
        self.assertEqual(ret['type_ids'], c.type_ids)
        self.assertEqual(ret['unit_filters'], expected_unit_filters)
        self.assertEqual(ret['remove_duplicates'], False)
        self.assertEqual(set(ret.keys()), ASSOCIATION_FIELDS)

    def test_from_dict(self):
        type_ids = ['rpm']
        unit_filters = {'some': 'filters', '$not': 'regexp?'}
        limit = 42
        skip = 64
        unit_fields = ['a_field']
        remove_duplicates = False
        association_fields = None
        unit_sort = None
        association_sort = None
        association_filters = {}
        a_dict = {'unit_filters': unit_filters, 'limit': limit, 'skip': skip,
                  'unit_fields': unit_fields, 'type_ids': type_ids,
                  'remove_duplicates': remove_duplicates, 'association_fields': association_fields,
                  'unit_sort': unit_sort, 'association_sort': association_sort,
                  'association_filters': association_filters}

        new_criteria = criteria.UnitAssociationCriteria.from_dict(a_dict)

        expected_unit_filters = {'some': 'filters', '$not': re.compile('regexp?')}
        self.assertTrue(isinstance(new_criteria, criteria.UnitAssociationCriteria))
        self.assertEqual(new_criteria.unit_filters, expected_unit_filters)
        self.assertEqual(new_criteria.association_sort, association_sort)
        self.assertEqual(new_criteria.limit, limit)
        self.assertEqual(new_criteria.type_ids, type_ids)
        self.assertEqual(new_criteria.unit_fields, unit_fields)
        self.assertEqual(new_criteria.skip, skip)
        self.assertEqual(new_criteria.remove_duplicates, remove_duplicates)
        self.assertEqual(new_criteria.unit_sort, unit_sort)
        self.assertEqual(new_criteria.association_filters, association_filters)
