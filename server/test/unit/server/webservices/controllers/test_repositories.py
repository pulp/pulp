"""
This module contains tests for the pulp.server.webservices.controllers.repositories module.
"""
import re
import unittest

import mock

from .... import base
from pulp.server.db.connection import PulpCollection
from pulp.server.db.model import criteria
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.db.model.repository import Repo
from pulp.server.managers import factory as manager_factory
from pulp.server.webservices.controllers import repositories


class RepoControllersTests(base.PulpWebserviceTests):
    def setUp(self):
        super(RepoControllersTests, self).setUp()
        self.repo_manager = manager_factory.repo_manager()

    def clean(self):
        super(RepoControllersTests, self).clean()
        Repo.get_collection().remove(safe=True)


class ReservedResourceApplyAsync(object):
    """
    This object allows us to mock the return value of _reserve_resource.apply_async.get().
    """

    def get(self):
        return 'some_queue'


class RepoSearchTests(RepoControllersTests):
    @mock.patch.object(repositories.RepoSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_basic_search(self, mock_query, mock_params):
        mock_params.return_value = {
            'criteria': {}
        }
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 200)
        self.assertEqual(mock_query.call_count, 1)
        query_arg = mock_query.call_args[0][0]
        self.assertTrue(isinstance(query_arg, criteria.Criteria))
        # one call each for criteria, importers, and distributors
        self.assertEqual(mock_params.call_count, 3)

    @mock.patch.object(PulpCollection, 'query')
    @mock.patch('pulp.server.db.model.criteria.Criteria.from_client_input')
    def test_get_details(self, mock_from_client, mock_query):
        status, body = self.get('/v2/repositories/search/?details=1&limit=2')
        self.assertEqual(status, 200)
        self.assertEquals(mock_from_client.call_count, 1)

        # make sure the non-criteria arguments aren't passed to the criteria
        # constructor
        criteria_args = mock_from_client.call_args[0][0]
        self.assertTrue('limit' in criteria_args)
        self.assertFalse('details' in criteria_args)
        self.assertFalse('importers' in criteria_args)

    @mock.patch.object(repositories.RepoSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_return_value(self, mock_query, mock_params):
        """
        make sure the method returns the same stuff that is returned by query()
        """
        mock_params.return_value = {
            'criteria': {}
        }
        mock_query.return_value = [
            {'id': 'repo-1'},
            {'id': 'repo-2'},
        ]
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 200)
        self.assertEqual(ret[1], mock_query.return_value)

    @mock.patch('pulp.server.webservices.controllers.repositories.RepoCollection._process_repos')
    @mock.patch.object(repositories.RepoSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_search_with_importers(self, mock_query, mock_params, mock_process_repos):
        mock_params.return_value = {
            'criteria': {},
            'importers': 1,
            'distributors': 0
        }
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 200)
        mock_process_repos.assert_called_once_with([], 1, 0)

    @mock.patch('pulp.server.webservices.controllers.repositories.RepoCollection._process_repos')
    @mock.patch.object(repositories.RepoSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_search_with_distributors(self, mock_query, mock_params, mock_process_repos):
        mock_params.return_value = {
            'criteria': {},
            'importers': 0,
            'distributors': 1
        }
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 200)
        mock_process_repos.assert_called_once_with([], 0, 1)

    @mock.patch('pulp.server.webservices.controllers.repositories.RepoCollection._process_repos')
    @mock.patch.object(repositories.RepoSearch, 'params')
    @mock.patch.object(PulpCollection, 'query')
    def test_search_with_both(self, mock_query, mock_params, mock_process_repos):
        mock_params.return_value = {
            'criteria': {},
            'importers': 1,
            'distributors': 1
        }
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 200)
        mock_process_repos.assert_called_once_with([], 1, 1)

    @mock.patch.object(repositories.RepoSearch, 'params', return_value={})
    def test_require_criteria(self, mock_params):
        """
        make sure this raises a MissingValue exception if 'criteria' is not
        passed as a parameter.
        """
        ret = self.post('/v2/repositories/search/')
        self.assertEqual(ret[0], 400)
        value = ret[1]
        self.assertTrue(isinstance(value, dict))
        self.assertTrue('missing_property_names' in value)
        self.assertEqual(value['missing_property_names'], [u'criteria'])

    @mock.patch.object(PulpCollection, 'query')
    def test_get(self, mock_query):
        """
        Make sure that we can do a criteria-based search with GET. Ensures that
        a proper Criteria object is created and passed to the collection's
        query method.
        """
        status, body = self.get(
            '/v2/repositories/search/?field=id&field=display_name&limit=20')
        self.assertEqual(status, 200)
        self.assertEqual(mock_query.call_count, 1)
        generated_criteria = mock_query.call_args[0][0]
        self.assertTrue(isinstance(generated_criteria, criteria.Criteria))
        self.assertEqual(len(generated_criteria.fields), 2)
        self.assertTrue('id' in generated_criteria.fields)
        self.assertTrue('display_name' in generated_criteria.fields)
        self.assertEqual(generated_criteria.limit, 20)
        self.assertTrue(generated_criteria.skip is None)


class RepoUnitAssociationQueryTests(RepoControllersTests):
    def setUp(self):
        super(RepoUnitAssociationQueryTests, self).setUp()
        self.repo_manager.create_repo('repo-1')

        self.association_query_mock = mock.Mock()
        manager_factory._INSTANCES[
            manager_factory.TYPE_REPO_ASSOCIATION_QUERY] = self.association_query_mock

    def clean(self):
        super(RepoUnitAssociationQueryTests, self).clean()
        manager_factory.reset()

    def test_post_single_type(self):
        """
        Passes in a full query document to test the parsing into criteria.
        """

        # Setup
        self.association_query_mock.get_units_by_type.return_value = []

        query = {
            'type_ids': ['rpm'],
            'filters': {
                'unit': {'key': {'$in': 'zsh'}},
                'association': {'some_field': 'some_value'}
            },
            'sort': {
                'unit': [['name', 'ascending'], ['version', '-1']],
                'association': [['created', '-1'], ['updated', '1']]
            },
            'limit': '100',
            'skip': '200',
            'fields': {
                'unit': ['name', 'version', 'arch'],
                'association': ['created']
            },
            'remove_duplicates': 'True'
        }

        params = {'criteria': query}
        status, body = self.post('/v2/repositories/repo-1/search/units/', params=params)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(0, self.association_query_mock.get_units_across_types.call_count)
        self.assertEqual(1, self.association_query_mock.get_units_by_type.call_count)

        criteria = self.association_query_mock.get_units_by_type.call_args[1]['criteria']
        self.assertTrue(isinstance(criteria, UnitAssociationCriteria))
        self.assertEqual(query['type_ids'], criteria.type_ids)
        self.assertEqual(query['filters']['association'], criteria.association_filters)
        self.assertEqual(query['filters']['unit'], criteria.unit_filters)
        self.assertEqual([('created', UnitAssociationCriteria.SORT_DESCENDING),
                          ('updated', UnitAssociationCriteria.SORT_ASCENDING)],
                         criteria.association_sort)
        self.assertEqual([('name', UnitAssociationCriteria.SORT_ASCENDING),
                          ('version', UnitAssociationCriteria.SORT_DESCENDING)], criteria.unit_sort)
        self.assertEqual(int(query['limit']), criteria.limit)
        self.assertEqual(int(query['skip']), criteria.skip)
        self.assertEqual(query['fields']['unit'], criteria.unit_fields)
        self.assertEqual(query['fields']['association'] + ['unit_id', 'unit_type_id'],
                         criteria.association_fields)
        self.assertEqual(bool(query['remove_duplicates']), criteria.remove_duplicates)

    def test_post_multiple_type(self):
        """
        Passes in a multiple typed query to ensure the correct manager method is called.
        """

        # Setup
        self.association_query_mock.get_units_across_types.return_value = []

        query = {'type_ids': ['rpm', 'errata']}

        params = {'criteria': query}
        status, body = self.post('/v2/repositories/repo-1/search/units/', params=params)

        # Verify
        self.assertEqual(200, status)

        self.assertEqual(0, self.association_query_mock.get_units_by_type.call_count)
        self.assertEqual(1, self.association_query_mock.get_units_across_types.call_count)
        self.assertTrue(
            isinstance(self.association_query_mock.get_units_across_types.call_args[1]['criteria'],
                       UnitAssociationCriteria))

    def test_post_missing_query(self):
        # Test
        status, body = self.post('/v2/repositories/repo-1/search/units/')

        # Verify
        self.assertEqual(status, 400)

    def test_post_bad_query(self):
        # Test
        params = {'criteria': {'limit': 'fus'}}
        status, body = self.post('/v2/repositories/repo-1/search/units/', params=params)

        # Verify
        self.assertEqual(400, status)


class UnitCriteriaTests(unittest.TestCase):
    def test_parse_criteria(self):
        # Setup
        query = {
            'type_ids': ['rpm'],
            'filters': {
                'unit': {'$and': [
                    {'$regex': '^p.*'},
                    {'$not': 'ython$'},
                ]},
                'association': {'created': {'$gt': 'now'}},
            },

            'limit': 100,
            'skip': 200,
            'fields': {
                'unit': ['name', 'version'],
                'association': ['created'],
            },
            'remove_duplicates': True,
        }

        # Test
        criteria = UnitAssociationCriteria.from_client_input(query)

        # Verify
        self.assertEqual(criteria.type_ids, ['rpm'])
        self.assertEqual(criteria.association_filters, {'created': {'$gt': 'now'}})
        self.assertEqual(criteria.limit, 100)
        self.assertEqual(criteria.skip, 200)
        self.assertEqual(criteria.unit_fields, ['name', 'version'])
        self.assertEqual(criteria.association_fields, ['created', 'unit_id', 'unit_type_id'])
        self.assertEqual(criteria.remove_duplicates, True)

        #   Check the special $not handling in the unit filter
        self.assertTrue('$and' in criteria.unit_filters)
        and_list = criteria.unit_filters['$and']

        self.assertTrue('$regex' in and_list[0])
        self.assertEqual(and_list[0]['$regex'], '^p.*')

        self.assertTrue('$not' in and_list[1])
        self.assertEqual(and_list[1]['$not'], re.compile('ython$'))
