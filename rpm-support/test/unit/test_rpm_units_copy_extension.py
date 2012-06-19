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

try:
    import json
except ImportError:
    import simplejson as json

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../../extensions/admin')

import rpm_support_base
import rpm_units_copy.pulp_cli

from pulp.bindings.responses import STATE_WAITING
from pulp.client.extensions.core import TAG_FAILURE, TAG_PARAGRAPH

class UnitCopyTests(rpm_support_base.PulpClientTests):

    def test_copy(self):
        # Setup
        command = rpm_units_copy.pulp_cli.CopyCommand(self.context, 'copy', 'copy', 'copy', 'rpm')
        task_data = {'task_id' : 'abc',
                     'task_group_id' : None,
                     'tags' : [],
                     'start_time' : None,
                     'finish_time' : None,
                     'response' : None,
                     'reasons' : [],
                     'state' : STATE_WAITING,
                     'progress' : None,
                     'result' : None,
                     'exception' : None,
                     'traceback' : None,
                     }
        self.server_mock.request.return_value = (202, task_data)

        # Test
        user_args = {
            'from-repo-id' : 'from-repo',
            'to-repo-id' : 'to-repo',
            'match' : ['name=pulp', 'version=1']
        }
        command.copy(**user_args)

        # Verify
        args = self.server_mock.request.call_args[0]
        self.assertEqual('POST', args[0])
        self.assertEqual('/pulp/api/v2/repositories/to-repo/actions/associate/', args[1])

        body = json.loads(args[2])
        self.assertEqual(body['source_repo_id'], 'from-repo')

        criteria = body['criteria']
        self.assertTrue(criteria is not None)
        self.assertEqual(criteria['type_ids'], ['rpm'])

        tags = self.prompt.get_write_tags()
        self.assertEqual(1, len(tags))
        self.assertEqual(tags[0], TAG_PARAGRAPH)

    def test_dry_run(self):
        # Setup
        command = rpm_units_copy.pulp_cli.CopyCommand(self.context, 'copy', 'copy', 'copy', 'rpm')
        self.server_mock.request.return_value = (200, {})

        # Test
        user_args = {
            'from-repo-id' : 'from-repo',
            'to-repo-id' : 'to-repo',
            'match' : ['name=pulp', 'version=1'],
            'dry-run' : True,
        }
        command.copy(**user_args)

        # Verify
        args = self.server_mock.request.call_args[0]
        self.assertEqual('POST', args[0])
        self.assertEqual('/pulp/api/v2/repositories/from-repo/search/units/', args[1])

    def test_bad_arguments(self):
        # Setup
        command = rpm_units_copy.pulp_cli.CopyCommand(self.context, 'copy', 'copy', 'copy', 'rpm')

        # Test
        user_args = {
            'from-repo-id' : 'from-repo',
            'to-repo-id' : 'to-repo',
            'match' : ['foo'],
        }
        command.copy(**user_args)

        # Verify
        tags = self.prompt.get_write_tags()
        self.assertEqual(1, len(tags))
        self.assertEqual(tags[0], TAG_FAILURE)

class ArgsToCriteriaTests(unittest.TestCase):

    def test_multiple_clauses(self):

        # With multiple clauses, all of the clauses in the unit filter will be
        # embedded in an $and clause.

        # Setup
        kwargs = {
            'match'  : ['name=^p.*'],
            'not'    : ['name=.*ython$', 'arch=i386'],
            'gt'     : ['version=1'],
            'gte'    : ['version=2'],
            'lt'     : ['version=10'],
            'lte'    : ['version=11'],
            'after'  : ['2012-05-01'],
            'before' : ['2012-05-31'],
        }
        type_id = 'rpm'

        # Test
        criteria = rpm_units_copy.pulp_cli.args_to_criteria(type_id, kwargs)

        # Verify
        self.assertEqual(criteria['type_ids'], [type_id])

        unit_filters = criteria['filters']['unit']
        and_clause = unit_filters['$and']
        self.assertEqual(7, len(and_clause))
        self.assertEqual(and_clause[0], {'name' : {'$regex' : '^p.*'}})
        self.assertEqual(and_clause[1], {'name' : {'$not' : '.*ython$'}})
        self.assertEqual(and_clause[2], {'arch' : {'$not' : 'i386'}})
        self.assertEqual(and_clause[3], {'version' : {'$gt' : '1'}})
        self.assertEqual(and_clause[4], {'version' : {'$gte' : '2'}})
        self.assertEqual(and_clause[5], {'version' : {'$lt' : '10'}})
        self.assertEqual(and_clause[6], {'version' : {'$lte' : '11'}})

    def test_single_unit_clause(self):

        # Make sure there's no $and present

        # Setup
        kwargs = {'match' : ['name=p.*']}

        # Test
        criteria = rpm_units_copy.pulp_cli.args_to_criteria('rpm', kwargs)

        # Verify
        unit_filters = criteria['filters']['unit']
        self.assertEqual(1, len(unit_filters))
        self.assertEqual(unit_filters['name'], {'$regex' : 'p.*'})

    def test_single_association_clause(self):

        # Setup
        kwargs = {'after' : '2012-05-01'}

        # Test
        criteria = rpm_units_copy.pulp_cli.args_to_criteria('rpm', kwargs)

        # Verify
        unit_filters = criteria['filters']['association']
        self.assertEqual(1, len(unit_filters))
        self.assertEqual(unit_filters['created'], {'$gte' : '2012-05-01'})

    def test_no_clauses(self):

        # Test
        criteria = rpm_units_copy.pulp_cli.args_to_criteria('rpm', {})

        # Verify
        self.assertEqual(criteria['type_ids'], ['rpm'])
        self.assertEqual(1, len(criteria))

    def test_invalid_argument(self):

        # Setup
        kwargs = {'match' : 'foo'}

        # Test
        self.assertRaises(rpm_units_copy.pulp_cli.InvalidCriteria, rpm_units_copy.pulp_cli.args_to_criteria, 'rpm', kwargs)
