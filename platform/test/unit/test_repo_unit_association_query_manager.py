#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import datetime
import math

import base
import mock

from pulp.common import dateutils
from pulp.plugins.types import database, model
from pulp.server.db.model.repository import RepoContentUnit
import pulp.server.managers.repo.unit_association as association_manager
from pulp.server.managers.repo.unit_association import OWNER_TYPE_USER, OWNER_TYPE_IMPORTER
import pulp.server.managers.repo.unit_association_query as association_query_manager
from pulp.server.managers.repo.unit_association_query import Criteria
import pulp.server.managers.content.cud as content_cud_manager
import pulp.server.managers.factory as manager_factory

# See test_get_units_by_type_not_query for an explanation as to why a webservice
# import is in a manager test. It's legit, I promise  :)
from pulp.server.webservices.serialization.unit_criteria import unit_association_criteria

# -- constants ----------------------------------------------------------------

TYPE_DEF_ALPHA = model.TypeDefinition('alpha', 'Alpha', 'Test Type Alpha',
    ['key_1'], ['search_1'], [])
TYPE_DEF_BETA = model.TypeDefinition('beta', 'Beta', 'Test Type Beta',
    ['key_1'], [], [])
TYPE_DEF_GAMMA = model.TypeDefinition('gamma', 'Gamma', 'Test Type Gamma',
    ['key_1'], [], [])
TYPE_DEF_DELTA = model.TypeDefinition('delta', 'Delta', 'Test Type Delta',
    ['key_1'], [], [])
TYPE_DEF_EPSILON = model.TypeDefinition('epsilon', 'Epsilon', 'Test Type Epsilon',
    ['key_1'], [], [])

_QUERY_TYPES = [TYPE_DEF_ALPHA, TYPE_DEF_BETA, TYPE_DEF_GAMMA, TYPE_DEF_DELTA, TYPE_DEF_EPSILON]

class UnitAssociationQueryTests(base.PulpServerTests):

    def clean(self):
        super(UnitAssociationQueryTests, self).clean()
        database.clean()
        RepoContentUnit.get_collection().remove()

    def setUp(self):
        super(UnitAssociationQueryTests, self).setUp()
        database.update_database(_QUERY_TYPES)
        self.manager = association_query_manager.RepoUnitAssociationQueryManager()
        self.association_manager = association_manager.RepoUnitAssociationManager()
        self.content_manager = content_cud_manager.ContentManager()
        # so we don't try to refresh the unit count on non-existing repos
        manager_factory._CLASSES[manager_factory.TYPE_REPO] = mock.MagicMock()
        self._populate()

    def tearDown(self):
        super(UnitAssociationQueryTests, self).tearDown()
        manager_factory.reset()

    def _populate(self):
        """
        Populates the database with units and associations with the
        following properties:

        - Units are from types: alpha, beta, gamma
        - Each unit has metadata:
          - key_1 - unique per unit per type (is the unit ID)
          - md_1 - unique per unit in a given type (simple counter)
          - md_2 - 0 or 1 depending on when it was added
          - md_3 - number of characters in the unit ID
        - All associations will have created/updated dates in ascending
          order according to alphabetical order

        - Alpha Units
          - Only associated once with repo-1
          - Association owner is type importer with ID test-importer
        - Beta Units
          - Only associated once with repo-1
          - Only associated once with repo-2 as well
          - Association owner is type user with ID admin
        - Gamma Units
          - Each associated twice with repo-1
          - One association is type importer with ID test-importer-2
          - One association is type user with ID admin-2
          - The user-created associations are older than the importer ones
        - Delta Units
          - Only associated with repo-2
          - Association owner is type importer with ID test-importer
        - Epsilon Units
          - Exist in the database but not associations
        """

        # -- test data --------

        self.units = {
            'alpha' : ['aardvark', 'anthill', 'apple',],
            'beta' : ['ball', 'balloon', 'bat', 'boardwalk'],
            'gamma' : ['garden', 'gnome'],
            'delta' : ['dog', 'dragon']
        }

        #   Generate timestamps 1 day apart in ascending order relative to now.
        #   The last entry is 1 day before now. Timestamps are already in iso8601.
        #     timestamps[x] < timestamps[x+1]

        now = datetime.datetime.now()
        self.timestamps = []
        for i in range(10, 0, -1):
            ts = now - datetime.timedelta(i)
            self.timestamps.append(dateutils.format_iso8601_datetime(ts))

        #   Assertions based on the test data
        self.repo_1_count = reduce(lambda x, y: x + len(self.units[y]), ['alpha', 'beta', 'gamma', 'gamma'], 0)
        self.repo_1_count_no_dupes = reduce(lambda x, y: x + len(self.units[y]), ['alpha', 'beta', 'gamma'], 0)
        self.repo_2_count = reduce(lambda x, y: x + len(self.units[y]), ['beta', 'delta'], 0)

        # -- add units --------

        for type_id, unit_ids in self.units.items():
            unit_ids.sort()
            for i, unit_id in enumerate(unit_ids):
                metadata = {
                    'key_1' : unit_id,
                    'md_1' : i,
                    'md_2' : i % 2,
                    'md_3' : len(unit_id),
                    }
                self.content_manager.add_content_unit(type_id, unit_id, metadata)

        # -- create associations --------

        def make_association(repo_id, type_id, unit_id, owner_type, owner_id, index):
            """
            Utility to perform standard association test data stuff such as
            setting the created/updated timestamps.
            """

            association_collection = RepoContentUnit.get_collection()
            self.association_manager.associate_unit_by_id(repo_id, type_id, unit_id, owner_type, owner_id)
            a = association_collection.find_one({'repo_id' : repo_id, 'unit_type_id' : type_id, 'unit_id' : unit_id})
            a['created'] = self.timestamps[index]
            a['updated'] = self.timestamps[index]
            association_collection.save(a, safe=True)

        #   Alpha
        for i, unit_id in enumerate(self.units['alpha']):
            make_association('repo-1', 'alpha', unit_id, OWNER_TYPE_IMPORTER, 'test-importer', i)

        #   Beta
        for i, unit_id in enumerate(self.units['beta']):
            make_association('repo-1', 'beta', unit_id, OWNER_TYPE_USER, 'admin', i)
            make_association('repo-2', 'beta', unit_id, OWNER_TYPE_USER, 'admin', i)

        #   Gamma
        for i, unit_id in enumerate(self.units['gamma']):
            make_association('repo-1', 'gamma', unit_id, OWNER_TYPE_IMPORTER, 'test-importer-2', i+1)
            make_association('repo-1', 'gamma', unit_id, OWNER_TYPE_USER, 'admin-2', i)

        #   Delta
        for i, unit_id in enumerate(self.units['delta']):
            make_association('repo-2', 'delta', unit_id, OWNER_TYPE_IMPORTER, 'test-importer', i)

    # -- get_unit_ids tests ---------------------------------------------------

    def test_get_unit_ids(self):

        # Setup
        repo_id = 'repo-1'
        units = {'type-1': ['1-1', '1-2', '1-3'],
                 'type-2': ['2-1', '2-2', '2-3']}

        for type_id, unit_ids in units.items():
            self.association_manager.associate_all_by_ids(repo_id, type_id, unit_ids, OWNER_TYPE_USER, 'admin')

        # Test - No Type
        all_units = self.manager.get_unit_ids(repo_id)

        # Verify - No Type
        self.assertTrue('type-1' in all_units)
        self.assertTrue('type-2' in all_units)
        self.assertEqual(3, len(all_units['type-1']))
        self.assertEqual(3, len(all_units['type-2']))

        # Test - By Type
        type_1_units = self.manager.get_unit_ids(repo_id, 'type-1')

        # Verify - By Type
        self.assertTrue('type-1' in type_1_units)
        self.assertFalse('type-2' in type_1_units)
        for id in units['type-1']:
            self.assertTrue(id in type_1_units['type-1'], '%s not in %s' % (id, ','.join(type_1_units['type-1'])))
        for id in type_1_units['type-1']:
            self.assertTrue(id in units['type-1'])

    # -- get_units tests ------------------------------------------------------

    class GetUnitsMock(association_query_manager.RepoUnitAssociationQueryManager):

        def __init__(self):
            self.called_get_units_by_type = False
            self.get_units_by_type_repo = None
            self.get_units_by_type_criteria = None

            self.called_get_units_across_types = False
            self.get_units_across_types_repo = None
            self.get_units_across_types_criteria = None

        def get_units_by_type(self, repo_id, type_id, criteria=None):
            self.called_get_units_by_type = True
            self.get_units_by_type_repo = repo_id
            self.get_units_by_type_criteria = criteria

        def get_units_across_types(self, repo_id, criteria=None):
            self.called_get_units_across_types = True
            self.get_units_across_types_repo = repo_id
            self.get_units_across_types_criteria = criteria

    def test_get_units_multiple_types(self):
        # Setup
        mock_manager = self.GetUnitsMock()

        # Test
        criteria = Criteria(type_ids=['fus', 'ro'])
        mock_manager.get_units('repo-1', criteria=criteria)

        # Verify
        self.assertTrue(mock_manager.called_get_units_across_types)
        self.assertFalse(mock_manager.called_get_units_by_type)

        self.assertEqual('repo-1', mock_manager.get_units_across_types_repo)
        self.assertEqual(criteria, mock_manager.get_units_across_types_criteria)

    def test_get_units_single_type(self):
        # Setup
        mock_manager = self.GetUnitsMock()

        # Test
        criteria = Criteria(type_ids=['fus'])
        mock_manager.get_units('repo-1', criteria=criteria)

        # Verify
        self.assertFalse(mock_manager.called_get_units_across_types)
        self.assertTrue(mock_manager.called_get_units_by_type)

        self.assertEqual('repo-1', mock_manager.get_units_by_type_repo)
        self.assertEqual(criteria, mock_manager.get_units_by_type_criteria)

    def test_get_units_no_criteria(self):
    # Setup
        mock_manager = self.GetUnitsMock()

        # Test
        mock_manager.get_units('repo-1')

        # Verify
        self.assertTrue(mock_manager.called_get_units_across_types)
        self.assertFalse(mock_manager.called_get_units_by_type)

        self.assertEqual('repo-1', mock_manager.get_units_across_types_repo)
        self.assertEqual(None, mock_manager.get_units_across_types_criteria)

    # -- get_units_across_types tests -----------------------------------------

    def test_get_units_no_criteria(self):
        # Test
        units_1 = self.manager.get_units_across_types('repo-1')
        units_2 = self.manager.get_units_across_types('repo-2')

        # Verify
        self.assertEqual(len(units_1), self.repo_1_count)
        self.assertEqual(len(units_2), self.repo_2_count)

        for u in units_1 + units_2:
            self._assert_unit_integrity(u)

        self._assert_default_sort(units_1)
        self._assert_default_sort(units_2)

    def test_get_units_filter_type(self):
        # Test
        criteria = Criteria(type_ids=['alpha', 'beta'])
        units = self.manager.get_units_across_types('repo-1', criteria)

        # Verify
        expected_count = reduce(lambda x, y: x + len(self.units[y]), ['alpha', 'beta'], 0)
        self.assertEqual(expected_count, len(units))

        for u in units:
            self._assert_unit_integrity(u)
            self.assertTrue(u['unit_type_id'] in ['alpha', 'beta']) # purpose of this test

        self._assert_default_sort(units)

    def test_get_units_filter_owner_type(self):
        # Test
        criteria = Criteria(association_filters={'owner_type' : OWNER_TYPE_IMPORTER})
        units = self.manager.get_units_across_types('repo-1', criteria)

        # Verify
        expected_count = reduce(lambda x, y: x + len(self.units[y]), ['alpha', 'gamma'], 0)
        self.assertEqual(expected_count, len(units))

    def test_get_units_limit(self):
        # Test
        low_criteria = Criteria(limit=2)
        low_units = self.manager.get_units_across_types('repo-1', low_criteria)

        high_criteria = Criteria(limit=10000)
        high_units = self.manager.get_units_across_types('repo-1', high_criteria)

        # Verify
        self.assertEqual(2, len(low_units))
        self.assertEqual(self.repo_1_count, len(high_units))

        #   Make sure the limit was applied to the front of the results
        self.assertEqual(low_units[0], high_units[0])
        self.assertEqual(low_units[1], high_units[1])

    def test_get_units_skip(self):
        # Test
        skip_criteria = Criteria(skip=2)
        skip_units = self.manager.get_units_across_types('repo-1', skip_criteria)

        all_units = self.manager.get_units_across_types('repo-1')

        # Verify
        self.assertEqual(self.repo_1_count -2, len(skip_units))

        # Make sure it was the first two that were actually skipped
        for su, au in zip(skip_units, all_units[2:]):
            self.assertEqual(su, au)

    def test_get_units_sort(self):
        # Test
        order_criteria = Criteria(association_sort=[('owner_type', association_manager.SORT_DESCENDING)]) # owner_type will produce a non-default sort
        order_units = self.manager.get_units_across_types('repo-1', order_criteria)

        # Verify
        self.assertEqual(self.repo_1_count, len(order_units))

        for i in range(0, len(order_units) - 1):
            u1 = order_units[i]
            u2 = order_units[i+1]
            self.assertTrue(u1['owner_type'] >= u2['owner_type'])

    def test_get_units_filter_created(self):
        # Test
        after_criteria = Criteria(association_filters={'created' : {'$gt' : self.timestamps[0]}})
        after_units = self.manager.get_units_across_types('repo-1', after_criteria)

        before_criteria = Criteria(association_filters={'created' : {'$lt' : self.timestamps[1]}})
        before_units = self.manager.get_units_across_types('repo-1', before_criteria)

        # Verify

        # The first association in each type/owner combination will be timestamps[0],
        # the second timestamps[1]. There are 4 such type/owner combinations,
        # however the user associations in gamma have timestamp offsets of i+1.

        self.assertEqual(self.repo_1_count - 3, len(after_units))
        self.assertEqual(3, len(before_units))

    def test_get_units_remove_duplicates(self):
        # Test
        criteria = Criteria(remove_duplicates=True)
        units = self.manager.get_units_across_types('repo-1', criteria)

        # Verify

        # The gamma units are associated twice, so they should only be returned once.
        self.assertEqual(self.repo_1_count - len(self.units['gamma']), len(units))

        # The gamma user associations were created at an earlier date, so all of
        # the gamma associations should be of owner type user.
        non_user_gamma_units = [u for u in units if u['unit_type_id'] == 'gamma' and u['owner_type'] != OWNER_TYPE_USER]
        self.assertEqual(0, len(non_user_gamma_units))

    def test_get_units_with_fields(self):
        # Test
        criteria = Criteria(association_fields=['owner_type'])
        units = self.manager.get_units_across_types('repo-1', criteria)

        # Verify
        for u in units:
            self.assertTrue('owner_type' in u)
            self.assertFalse('owner_id' in u)
            self.assertFalse('created' in u)
            self.assertFalse('updated' in u)

    # -- get_units_by_type tests ----------------------------------------------

    def test_get_units_by_type_no_criteria(self):
        # Test
        alpha_units = self.manager.get_units_by_type('repo-1', 'alpha')
        beta_units = self.manager.get_units_by_type('repo-1', 'beta')
        epsilon_units = self.manager.get_units_by_type('repo-1', 'epsilon')

        # Verify
        self.assertEqual(len(self.units['alpha']), len(alpha_units))
        self.assertEqual(len(self.units['beta']), len(beta_units))
        self.assertEqual(0, len(epsilon_units))

        for u in alpha_units + beta_units:
            self._assert_unit_integrity(u)

        self._assert_default_sort(alpha_units)
        self._assert_default_sort(beta_units)

    def test_get_units_by_type_association_filter(self):
        # Test
        criteria = Criteria(association_filters={'owner_type' : OWNER_TYPE_IMPORTER})
        units = self.manager.get_units_by_type('repo-1', 'gamma', criteria)

        # Verify

        # There are two associations for each gamma unit, one for importer and
        # one for unit. This verification is that only the importer set of them
        # is returned, so the expected length is 1x gamma insetad of 2x.
        self.assertEqual(len(self.units['gamma']), len(units))

        for u in units:
            self.assertEqual(u['owner_type'], association_manager.OWNER_TYPE_IMPORTER)

    def test_get_units_by_type_unit_metadata_filter(self):
        # Test
        criteria = Criteria(unit_filters={'md_2' : 0})
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        expected = math.ceil(float(len(self.units['alpha'])) / float(2))
        self.assertEqual(expected, len(units))

        for u in units:
            self.assertEqual(u['metadata']['md_2'], 0)

    def test_get_units_by_type_filter_wildcard(self):
        # Test
        criteria = Criteria(unit_filters={'key_1' : {'$regex' : 'aa.*'}})
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        self.assertEqual(1, len(units))
        self.assertEqual('aardvark', units[0]['metadata']['key_1'])

    def test_get_units_by_type_association_sort_limit(self):
        # Test
        criteria = Criteria(association_sort=[('owner_type', association_manager.SORT_DESCENDING)], limit=2)
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        self.assertEqual(2, len(units))
        for i in range(0, len(units) - 1):
            u1 = units[i]
            u2 = units[i+1]
            self.assertTrue(u1['owner_type'] >= u2['owner_type'])

    def test_get_units_by_type_unit_metadata_sort_limit(self):
        # Test
        criteria = Criteria(unit_sort=[('md_2', association_manager.SORT_DESCENDING)], limit=2)
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        self.assertEqual(2, len(units))
        self.assertEqual(2, len(units))
        for i in range(0, len(units) - 1):
            u1 = units[i]
            u2 = units[i+1]
            self.assertTrue(u1['metadata']['md_2'] >= u2['metadata']['md_2'])

    def test_get_units_by_type_association_sort_skip(self):
        # Test
        criteria = Criteria(association_sort=[('owner_type', association_manager.SORT_DESCENDING)], skip=1)
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        expected_count = len(self.units['alpha']) - 1 # skip the first
        self.assertEqual(expected_count, len(units))

    def test_get_units_by_type_unit_metadata_sort_skip(self):
        # Test
        criteria = Criteria(unit_sort=[('md_2', association_manager.SORT_DESCENDING)], skip=1)
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        expected_count = len(self.units['alpha']) - 1 # skip the first
        self.assertEqual(expected_count, len(units))

    def test_get_units_by_type_sort_association_data(self):
        # Test
        sort_criteria = Criteria(association_sort=[('created', association_manager.SORT_DESCENDING)])
        sort_units = self.manager.get_units_by_type('repo-1', 'alpha', sort_criteria)

        # Verify
        self.assertEqual(len(self.units['alpha']), len(sort_units))

        for i in range(0, len(sort_units) - 1):
            u1 = sort_units[i]
            u2 = sort_units[i+1]
            self.assertTrue(u1['created'] >= u2['created'])

    def test_get_units_by_type_sort_unit_data(self):
        # Test
        sort_criteria = Criteria(unit_sort=[('md_2', association_manager.SORT_DESCENDING)])
        sort_units = self.manager.get_units_by_type('repo-1', 'alpha', sort_criteria)

        # Verify
        self.assertEqual(len(self.units['alpha']), len(sort_units))

        for i in range(0, len(sort_units) - 1):
            u1 = sort_units[i]
            u2 = sort_units[i+1]
            self.assertTrue(u1['metadata']['md_2'] >= u2['metadata']['md_2'])

    def test_get_units_by_type_remove_duplicates(self):
        # Test
        criteria = Criteria(remove_duplicates=True)
        units = self.manager.get_units_by_type('repo-1', 'gamma', criteria)

        # Verify
        self.assertEqual(len(self.units['gamma']), len(units)) # only one association per gamma unit
        for u in units:
            self.assertEqual(u['owner_type'], association_manager.OWNER_TYPE_USER) # all user associations have earlier created date

    def test_get_units_by_type_with_assoc_fields(self):
        # Test
        criteria = Criteria(association_fields=['owner_type'])
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        for u in units:
            self.assertTrue('owner_type' in u)
            self.assertFalse('owner_id' in u)
            self.assertFalse('created' in u)

            # Make sure the unit fields are untouched by the filter
            self.assertTrue('key_1' in u['metadata'])
            self.assertTrue('md_1' in u['metadata'])

    def test_get_units_by_type_with_unit_fields(self):
        # Test
        criteria = Criteria(unit_fields=['key_1', 'md_1'])
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        for u in units:
            # Make sure the association fields are untouched by the filter
            self.assertTrue('owner_type' in u)
            self.assertTrue('owner_id' in u)
            self.assertTrue('created' in u)

            self.assertTrue('key_1' in u['metadata'])
            self.assertTrue('md_1' in u['metadata'])
            self.assertFalse('md_2' in u['metadata'])
            self.assertFalse('md_3' in u['metadata'])

    def test_get_units_by_type_not_query(self):
        """
        Mongo really doesn't like $not queries when regular expressions are
        involved. This test is to make sure that across mongo and pymongo
        versions a not expression against a regular expression continues to
        work.

        There is an important step in the parsing of the criteria from the
        REST call into the Criteria object. This call will use that method
        to more closely test the end to end experience.
        """

        # Setup

        # I got bit by the fact that incoming REST requests are in unicode;
        # the criteria parsing didn't account for this. This example specifically
        # replicates that by having the not and its value in unicode.

        query_string = {
            'filters' : {
                'unit' : {
                    'key_1' : {
                        u'$not' : u'.*aa.*'
                    }
                }
            }
        }
        criteria = unit_association_criteria(query_string)

        # Test
        units = self.manager.get_units_by_type('repo-1', 'alpha', criteria)

        # Verify
        self.assertEqual(len(self.units['alpha']) - 1, len(units))
        for u in units:
            self.assertTrue(u['metadata']['key_1'] != 'aardvark')

    def test_remove_duplicates(self):
        # Setup
        def unit(unit_type_id, unit_id, created):
            return {'unit_type_id' : unit_type_id,
                    'unit_id' : unit_id,
                    'created' : created}

        all_units = [
            unit('t1', 'u1', self.timestamps[2]),
            unit('t1', 'u1', self.timestamps[1]),
            unit('t1', 'u1', self.timestamps[3]),
            unit('t1', 'u2', self.timestamps[6]),
            unit('t2', 'u1', self.timestamps[5]),
            ]

        # Test
        matching = self.manager._remove_duplicate_associations(all_units)

        # Verify
        self.assertEqual(3, len(matching))
        self.assertEqual(matching[0]['unit_type_id'], 't1')
        self.assertEqual(matching[0]['unit_id'], 'u1')
        self.assertEqual(matching[0]['created'], self.timestamps[1])
        self.assertEqual(matching[1]['unit_type_id'], 't1')
        self.assertEqual(matching[1]['unit_id'], 'u2')
        self.assertEqual(matching[1]['created'], self.timestamps[6])
        self.assertEqual(matching[2]['unit_type_id'], 't2')
        self.assertEqual(matching[2]['unit_id'], 'u1')
        self.assertEqual(matching[2]['created'], self.timestamps[5])

    def test_criteria_str(self):
        # Setup
        c1 = Criteria()
        c2 = Criteria(type_ids=['a'], association_filters={'a':'a'}, unit_filters={'b':'b'},
                      association_sort=['c'], unit_sort=['d'], limit=1, skip=2, association_fields=['e'],
                      unit_fields=['f'], remove_duplicates=True)

        # Test no exceptions are raised
        str(c1)
        str(c2)

    def test_criteria_init(self):
        # Test
        c = Criteria(type_ids='single')
        self.assertEqual(['single'], c.type_ids)

    # -- utilities ------------------------------------------------------------

    def _assert_unit_integrity(self, unit):
        """
        Makes sure all of the expected fields are present in the unit and that
        it is assembled correctly. This call has a limited concept of what the
        values should be but will do some tests were possible.

        This call will have to change if the returned structure of the units is
        changed.
        """

        self.assertTrue(unit['repo_id'] is not None)
        self.assertTrue(unit['unit_type_id'] is not None)
        self.assertTrue(unit['unit_id'] is not None)
        self.assertTrue(unit['owner_type'] is not None)
        self.assertTrue(unit['owner_id'] is not None)
        self.assertTrue(unit['created'] is not None)
        self.assertTrue(unit['updated'] is not None)

        self.assertTrue(unit['metadata'] is not None)
        self.assertTrue(unit['metadata']['key_1'] is not None)
        self.assertTrue(unit['metadata']['md_1'] is not None)
        self.assertTrue(unit['metadata']['md_2'] is not None)
        self.assertTrue(unit['metadata']['md_3'] is not None)

    def _assert_default_sort(self, units):
        """
        Asserts that units are sorted first by type, then by created within
        each type.
        """

        for i in range(0, len(units) - 1):
            u1 = units[i]
            u2 = units[i+1]
            self.assertTrue(u1['unit_type_id'] <= u2['unit_type_id'])

        units_by_type = {}
        for u in units:
            x = units_by_type.setdefault(u['unit_type_id'], [])
            x.append(u)

        for units_list in units_by_type.values():
            for i in range(0, len(units_list) - 1):
                u1 = units_list[i]
                u2 = units_list[i+1]
                self.assertTrue(u1['created'] <= u2['created'])

# -- stress tests -------------------------------------------------------------

class GetUnitsStressTest(base.PulpServerTests):

    ENABLED = False

    def clean(self):
        super(GetUnitsStressTest, self).clean()
        database.clean()
        RepoContentUnit.get_collection().remove()

    def setUp(self):
        super(GetUnitsStressTest, self).setUp()
        database.update_database(_QUERY_TYPES)
        self.manager = association_query_manager.RepoUnitAssociationQueryManager()
        self.association_manager = association_manager.RepoUnitAssociationManager()
        self.content_manager = content_cud_manager.ContentManager()

    def test_1(self):
        """
        Scenario: Simulates around 4 completely unique base channels and
        searching for all units in one of them.

        Test Properties:
        - 12000 units, single unit type, 10 metadata keys each
        - 3000 associations, importer owned
        """

        if not GetUnitsStressTest.ENABLED: return

        # Setup
        repo_id = 'repo-1'

        start = datetime.datetime.now()
        for i in range(0, 12000):
            unit_id = 'unit_%d' % i
            metadata = {'key_1' : unit_id}
            for j in range(0, 10):
                metadata['md_%d' % j] = 'value_%d' % i
            self.content_manager.add_content_unit('alpha', unit_id, metadata)

        for i in range(3000, 6000):
            unit_id = 'unit_%d' % i
            self.association_manager.associate_unit_by_id(repo_id, 'alpha', unit_id, association_manager.OWNER_TYPE_IMPORTER, 'stress-importer')

        end = datetime.datetime.now()
        setup_ellapsed = (end - start).seconds

        # Test
        start = datetime.datetime.now()
        units = self.manager.get_units_across_types(repo_id)
        self.assertEqual(3000, len(units))
        end = datetime.datetime.now()
        test_ellapsed = (end - start).seconds

        print('Scenario 1: Test ran in [%d] seconds. Setup ran in [%d] seconds.' % (test_ellapsed, setup_ellapsed))

    def test_2(self):
        """
        Scenario: Abnormally large repository with all 15,000 units spread out
        across 5 unit types.

        Test Properties:
        - 15000 units balanced across 5 unit types, 30 metadata keys each
        - 15000 associations, importer owned
        """

        if not GetUnitsStressTest.ENABLED: return

        # Setup
        repo_id = 'repo-2'

        start = datetime.datetime.now()
        for i in range(0, 15000):
            unit_id = 'unit_%d' % i
            unit_type_id = _QUERY_TYPES[i % len(_QUERY_TYPES)].id
            metadata = {'key_1' : unit_id}
            for j in range(0, 30):
                metadata['md_%d' % j] = 'value_%d' % i
            self.content_manager.add_content_unit(unit_type_id, unit_id, metadata)
            self.association_manager.associate_unit_by_id(repo_id, unit_type_id, unit_id, association_manager.OWNER_TYPE_IMPORTER, 'stress-importer')

        end = datetime.datetime.now()
        setup_ellapsed = (end - start).seconds

        # Test
        start = datetime.datetime.now()
        units = self.manager.get_units_across_types(repo_id)
        self.assertEqual(15000, len(units))
        end = datetime.datetime.now()
        test_ellapsed = (end - start).seconds

        print('Scenario 2: Test ran in [%d] seconds. Setup ran in [%d] seconds.' % (test_ellapsed, setup_ellapsed))

    def test_3(self):
        """
        Scenario: Absurdly large repository with all 50,000 units spread out
        across 5 unit types.

        Test Properties:
        - 50000 units balanced across 5 unit types, 30 metadata keys each
        - 50000 associations, importer owned
        """

        if not GetUnitsStressTest.ENABLED: return

        # Setup
        repo_id = 'repo-2'

        start = datetime.datetime.now()
        for i in range(0, 50000):
            unit_id = 'unit_%d' % i
            unit_type_id = _QUERY_TYPES[i % len(_QUERY_TYPES)].id
            metadata = {'key_1' : unit_id}
            for j in range(0, 30):
                metadata['md_%d' % j] = 'value_%d' % i
            self.content_manager.add_content_unit(unit_type_id, unit_id, metadata)
            self.association_manager.associate_unit_by_id(repo_id, unit_type_id, unit_id, association_manager.OWNER_TYPE_IMPORTER, 'stress-importer')

        end = datetime.datetime.now()
        setup_ellapsed = (end - start).seconds

        # Test
        start = datetime.datetime.now()
        units = self.manager.get_units_across_types(repo_id)
        self.assertEqual(50000, len(units))
        end = datetime.datetime.now()
        test_ellapsed = (end - start).seconds

        print('Scenario 3: Test ran in [%d] seconds. Setup ran in [%d] seconds.' % (test_ellapsed, setup_ellapsed))

    def test_4(self):
        """
        Scenario: Standard repository size but all associations are duplicated
        (unlikely in the real world). Criteria set to remove duplicates.

        Test Properties:
        - 3000 units, single unit type
        - 2 associations per unit
        - Criteria removes duplicates
        """

        if not GetUnitsStressTest.ENABLED: return

        # Setup
        repo_id = 'repo-3'

        start = datetime.datetime.now()
        for i in range(0, 3000):
            unit_id = 'unit_%d' % i
            metadata = {'key_1' : unit_id}
            for j in range(0, 10):
                metadata['md_%d' % j] = 'value_%d' % i
            self.content_manager.add_content_unit('alpha', unit_id, metadata)

            self.association_manager.associate_unit_by_id(repo_id, 'alpha', unit_id, association_manager.OWNER_TYPE_IMPORTER, 'stress-importer')
            self.association_manager.associate_unit_by_id(repo_id, 'alpha', unit_id, association_manager.OWNER_TYPE_USER, 'admin')

        end = datetime.datetime.now()
        setup_ellapsed = (end - start).seconds

        # Test
        start = datetime.datetime.now()
        criteria = Criteria(remove_duplicates=True)
        units = self.manager.get_units_across_types(repo_id, criteria)
        self.assertEqual(3000, len(units))
        end = datetime.datetime.now()
        test_ellapsed = (end - start).seconds

        print('Scenario 4: Test ran in [%d] seconds. Setup ran in [%d] seconds.' % (test_ellapsed, setup_ellapsed))

class GetUnitsByTypeStressTest(base.PulpServerTests):

    ENABLED = False

    def clean(self):
        super(GetUnitsByTypeStressTest, self).clean()
        database.clean()
        RepoContentUnit.get_collection().remove()

    def setUp(self):
        super(GetUnitsByTypeStressTest, self).setUp()
        database.update_database(_QUERY_TYPES)
        self.manager = association_query_manager.RepoUnitAssociationQueryManager()
        self.association_manager = association_query_manager.RepoUnitAssociationQueryManager()
        self.content_manager = content_cud_manager.ContentManager()

    def test_1(self):
        """
        Scenario: Repositories of increasing size retrieving units of a given
        type.
        """
        if not GetUnitsByTypeStressTest.ENABLED: return

        repo_id = 'repo-1'

        header = 'Query Time   Total Num Units   Units per Type   Setup Time'
        report = '%+10s   %+15s   %+14s   %+10s'

        print('Scenario: Retrieving all units of a given type from a repository')
        print('----------------------------------------------------------------')
        print(header)

        offset = 0
        step = 3000
        limit = 21000
        different_types = 3
        metadata_fields = 10

        for i in range(0, limit, step):

            # Setup
            start = datetime.datetime.now()
            for j in range(offset + i, offset + i + step):
                unit_id = 'unit_%d' % j
                unit_type_id = _QUERY_TYPES[j % different_types].id
                metadata = {'key_1' : unit_id}
                for k in range(0, metadata_fields):
                    metadata['md_%d' % k] = 'value_%d' % k

                self.content_manager.add_content_unit(unit_type_id, unit_id, metadata)
                self.association_manager.associate_unit_by_id(repo_id, unit_type_id, unit_id, association_manager.OWNER_TYPE_IMPORTER, 'stress-importer')

            end = datetime.datetime.now()
            setup_ellapsed = (end - start).seconds

            # Test
            start = datetime.datetime.now()
            units = self.manager.get_units_by_type(repo_id, _QUERY_TYPES[0].id)

            expected_count = (offset + step) / different_types
            self.assertEqual(expected_count, len(units))

            end = datetime.datetime.now()
            test_ellapsed = (end - start).seconds

            offset += step

            print(report % (test_ellapsed, offset, (offset / different_types), setup_ellapsed))

        print('')

    def test_2(self):
        """
        Scenario: Filtering by association and unit metdata, both indexed and
        non-indexed unit metadata.
        """
        if not GetUnitsByTypeStressTest.ENABLED: return

        repo_id = 'repo-2'

        header = 'Query Time   Query Type   Total Num Units   Matching   Setup Time'
        report = '%+10s   %+10s   %+15s   %+8s   %+10s'

        print('Scenario: Filtering by association and unit metadata, both indexed and non-indexed, with limited unit metadata')
        print('--------------------------------------------------------------------------------------------------------------')
        print(header)

        offset = 0
        step = 3000
        limit = 21000
        metadata_fields = 5
        match_frequency = 3 # search field values will mod over this number

        for i in range(0, limit, step):

            # Setup
            start = datetime.datetime.now()
            for j in range(offset + i, offset + i + step):
                unit_id = 'unit_%d' % j
                unit_type_id = 'alpha'
                metadata = {'key_1' : unit_id,
                            'search_1' : 'search_%d' % (j % match_frequency),
                            'non_search_1' : 'non_search_%d' % (j % match_frequency)}
                for k in range(0, metadata_fields - 3):
                    metadata['md_%d' % j] = 'value_%d' % k
                self.content_manager.add_content_unit(unit_type_id, unit_id, metadata)
                if (j % match_frequency) is 0:
                    owner_type = OWNER_TYPE_IMPORTER
                else:
                    owner_type = OWNER_TYPE_USER
                self.association_manager.associate_unit_by_id(repo_id, unit_type_id, unit_id, owner_type, 'stress')

            end = datetime.datetime.now()
            setup_ellapsed = (end - start).seconds

            # Test

            #   Association Query
            start = datetime.datetime.now()
            criteria = Criteria(association_filters={'owner_type' : OWNER_TYPE_IMPORTER})
            units = self.manager.get_units_by_type(repo_id, 'alpha', criteria)

            expected_count = (offset + step) / match_frequency
            self.assertEqual(expected_count, len(units))

            end = datetime.datetime.now()
            association_ellapsed = (end - start).seconds

            #   Index Query
            start = datetime.datetime.now()
            criteria = Criteria(unit_filters={'search_1' : 'search_0'})
            units = self.manager.get_units_by_type(repo_id, 'alpha', criteria)

            expected_count = (offset + step) / match_frequency
            self.assertEqual(expected_count, len(units))

            end = datetime.datetime.now()
            index_ellapsed = (end - start).seconds

            #   Non-index Query
            start = datetime.datetime.now()
            criteria = Criteria(unit_filters={'non_search_1' : 'non_search_0'})
            units = self.manager.get_units_by_type(repo_id, 'alpha', criteria)

            expected_count = (offset + step) / match_frequency
            self.assertEqual(expected_count, len(units))

            end = datetime.datetime.now()
            non_index_ellapsed = (end - start).seconds

            offset += step

            print(report % (association_ellapsed, 'Assoc', offset, (offset / match_frequency), setup_ellapsed))
            print(report % (index_ellapsed, 'Index', offset, (offset / match_frequency), setup_ellapsed))
            print(report % (non_index_ellapsed, 'Non-index', offset, (offset / match_frequency), setup_ellapsed))

        print('')

    def _run_sort_test(self, repo_id, step, limit, metadata_fields, sort_entropy):
        """
        @param repo_id: repo to associate against
        @type  repo_id: str

        @param step: number of units to process before running the queries
        @type  step: int

        @param limit: total number of units to have in the system before stopping
        @type  limit: int

        @param metadata_fields: number of metadata fields to add per unit
        @type  metadata_fields: int

        @param sort_entropy: number of unique values to use in the search fields
        @type  sort_entropy: int
        """

        if not GetUnitsByTypeStressTest.ENABLED: return

        header = 'Query Time   Query Type   Total Num Units   Setup Time'
        report = '%+10s   %+10s   %+15s   %+10s'

        print(header)

        offset = 0
        for i in range(0, limit, step):

            # Setup
            start = datetime.datetime.now()
            for j in range(offset + i, offset + i + step):
                unit_id = 'unit_%d' % j
                unit_type_id = 'alpha'
                metadata = {'key_1' : unit_id,
                            'search_1' : 'search_%d' % (j % sort_entropy),
                            'non_search_1' : 'non_search_%d' % (j % sort_entropy)}
                for k in range(0, metadata_fields - 3):
                    metadata['md_%d' % k] = 'value_%d' % k
                self.content_manager.add_content_unit(unit_type_id, unit_id, metadata)
                owner_id = 'owner_%d' % (j % sort_entropy)
                self.association_manager.associate_unit_by_id(repo_id, unit_type_id, unit_id, OWNER_TYPE_USER, owner_id)

            end = datetime.datetime.now()
            setup_ellapsed = (end - start).seconds

            # Test
            expected_count = (offset + step)

            #   Association Indexed Query
            try:
                start = datetime.datetime.now()
                criteria = Criteria(association_sort=[('unit_type_id', association_manager.SORT_DESCENDING), ('created', association_manager.SORT_DESCENDING)])

                units = self.manager.get_units_by_type(repo_id, 'alpha', criteria)

                self.assertEqual(expected_count, len(units))

                end = datetime.datetime.now()
                association_index_ellapsed = (end - start).seconds
            except:
                association_index_ellapsed = 'Failed'

            #   Association Non-Indexed Query
            try:
                start = datetime.datetime.now()
                criteria = Criteria(association_sort=[('owner_id', association_manager.SORT_DESCENDING)])

                units = self.manager.get_units_by_type(repo_id, 'alpha', criteria)

                self.assertEqual(expected_count, len(units))

                end = datetime.datetime.now()
                association_non_index_ellapsed = (end - start).seconds
            except:
                association_non_index_ellapsed = 'Failed'

            #   Index Query
            try:
                start = datetime.datetime.now()
                criteria = Criteria(unit_sort=[('search_1', association_manager.SORT_DESCENDING)])

                units = self.manager.get_units_by_type(repo_id, 'alpha', criteria)

                self.assertEqual(expected_count, len(units))

                end = datetime.datetime.now()
                index_ellapsed = (end - start).seconds
            except:
                index_ellapsed = 'Failed'

            #   Non-index Query
            try:
                start = datetime.datetime.now()
                criteria = Criteria(unit_sort=[('non_search_1', association_manager.SORT_DESCENDING)])

                units = self.manager.get_units_by_type(repo_id, 'alpha', criteria)

                self.assertEqual(expected_count, len(units))

                end = datetime.datetime.now()
                non_index_ellapsed = (end - start).seconds
            except:
                non_index_ellapsed = 'Failed'

            offset += step

            print(report % (association_index_ellapsed, 'Assoc Ind', offset, setup_ellapsed))
            print(report % (association_non_index_ellapsed, 'Assoc Non', offset, setup_ellapsed))
            print(report % (index_ellapsed, 'Unit Ind', offset, setup_ellapsed))
            print(report % (non_index_ellapsed, 'Unit Non', offset, setup_ellapsed))
            print('')

    def test_3(self):
        print('-------------------------------------------------------------------------')
        print('Scenario: Sorting with 5 metadata fields per unit and sort entropy at 100')
        print('-------------------------------------------------------------------------')

        repo_id = 'repo-3'
        step = 3000
        limit = 21000
        metadata_fields = 5
        sort_entropy = 100 # number of unique fields in the sort column

        self._run_sort_test(repo_id, step, limit, metadata_fields, sort_entropy)

    def test_4(self):
        print('--------------------------------------------------------------------------')
        print('Scenario: Sorting with 25 metadata fields per unit and sort entropy at 100')
        print('--------------------------------------------------------------------------')

        repo_id = 'repo-4'
        step = 3000
        limit = 21000
        metadata_fields = 25
        sort_entropy = 100

        self._run_sort_test(repo_id, step, limit, metadata_fields, sort_entropy)

    def test_5(self):
        print('--------------------------------------------------------------------------')
        print('Scenario: Sorting with 50 metadata fields per unit and sort entropy at 100')
        print('--------------------------------------------------------------------------')

        repo_id = 'repo-5'
        step = 3000
        limit = 21000
        metadata_fields = 50
        sort_entropy = 100

        self._run_sort_test(repo_id, step, limit, metadata_fields, sort_entropy)

    def test_6(self):
        print('---------------------------------------------------------------------------')
        print('Scenario: Sorting with 10 metadata fields per unit and sort entropy at 2500')
        print('---------------------------------------------------------------------------')

        repo_id = 'repo-5'
        step = 3000
        limit = 21000
        metadata_fields = 10
        sort_entropy = 2500

        self._run_sort_test(repo_id, step, limit, metadata_fields, sort_entropy)

    def test_7(self):
        print('---------------------------------------------------------------------------')
        print('Scenario: Sorting with 50 metadata fields per unit and sort entropy at 2500')
        print('---------------------------------------------------------------------------')

        repo_id = 'repo-7'
        step = 3000
        limit = 21000
        metadata_fields = 50
        sort_entropy = 2500

        self._run_sort_test(repo_id, step, limit, metadata_fields, sort_entropy)
