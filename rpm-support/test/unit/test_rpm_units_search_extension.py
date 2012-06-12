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

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../../extensions')

import base
import rpm_units_search.pulp_cli

class GeneralUnitSearchCommandTests(base.PulpClientTests):

    def test_search(self):
        # Setup
        command = rpm_units_search.pulp_cli.GeneralUnitSearchCommand(self.context, 'name', 'desc', 'title', ['rpm'])
        self.server_mock.request.return_value = (200, {})

        # Test
        command.search(**{'repo-id' : 'repo-1'})

        # Verify
        # TODO: ran out of time, revisit in the future

        # Cleanup
        self.server_mock.request.return_value = None

class RpmUnitsSearchUtilityTests(base.PulpClientTests):

    def test_args_to_criteria_doc_empty_args(self):
        # Setup
        args = {}
        type_ids = ['rpm']

        # Test
        criteria = rpm_units_search.pulp_cli.args_to_criteria_doc(args, type_ids)

        # Verify
        self.assertTrue(isinstance(criteria, dict))
        self.assertEqual(1, len(criteria))
        self.assertEqual(criteria['type_ids'], type_ids)

    def test_args_to_criteria_doc(self):
        # Setup
        args = {
            'fields' : 'name,version',
            'ascending' : 'name,arch',
            'descending' : 'arch,name',
            'limit' : '10',
            'skip' : '5',
        }
        type_ids = ['rpm']

        # Test
        criteria = rpm_units_search.pulp_cli.args_to_criteria_doc(args, type_ids)

        # Verify
        self.assertEqual(criteria['type_ids'], type_ids)
        self.assertEqual(criteria['fields']['unit'], ['name', 'version'])
        self.assertEqual(criteria['sort']['unit'], [ ['name', 'ascending'], ['arch', 'ascending']])
        self.assertEqual(criteria['limit'], 10)
        self.assertEqual(criteria['skip'], 5)

        # Descending has no effect since ascending is specified

    def test_args_to_criteria_doc_descending(self):
        # Setup
        args = {
            'descending' : 'arch,name',
        }
        type_ids = ['rpm']

        # Test
        criteria = rpm_units_search.pulp_cli.args_to_criteria_doc(args, type_ids)

        # Verify
        self.assertEqual(criteria['type_ids'], type_ids)
        self.assertEqual(criteria['sort']['unit'], [ ['arch', 'descending'], ['name', 'descending']])

    def test_args_to_criteria_doc_invalid_fields(self):
        # Setup
        args = {
            'fields' : 'invalid_field'
        }

        # Test
        self.assertRaises(rpm_units_search.pulp_cli.InvalidCriteria, rpm_units_search.pulp_cli.args_to_criteria_doc, args, ['rpm'])

    def test_args_to_criteria_doc_invalid_limit(self):
        # Setup
        args = {
            'limit' : 'unparsable'
        }

        # Test
        self.assertRaises(rpm_units_search.pulp_cli.InvalidCriteria, rpm_units_search.pulp_cli.args_to_criteria_doc, args, ['rpm'])

    def test_args_to_criteria_doc_invalid_skip(self):
        # Setup
        args = {
            'skip' : 'unparsable'
        }

        # Test
        self.assertRaises(rpm_units_search.pulp_cli.InvalidCriteria, rpm_units_search.pulp_cli.args_to_criteria_doc, args, ['rpm'])

