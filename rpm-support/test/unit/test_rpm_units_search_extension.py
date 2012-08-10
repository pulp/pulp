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
import unittest

import mock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../../extensions/admin')

import rpm_support_base
import rpm_units_search.pulp_cli

class TestUnitSection(unittest.TestCase):
    def setUp(self):
        rpm_units_search.pulp_cli.CONTEXT = mock.MagicMock()
        rpm_units_search.pulp_cli.CONTEXT.server = mock.MagicMock()

    def test_content_command(self):
        # setup
        return_value = mock.MagicMock()
        return_value.response_body = ['unit1']
        rpm_units_search.pulp_cli.CONTEXT.server.repo_unit.search.return_value = return_value

        rpm_units_search.pulp_cli._content_command(['rpm'], **{'repo-id': 'repo1'})
        rpm_units_search.pulp_cli.CONTEXT.server.repo_unit.search.assert_called_once_with('repo1', type_ids=['rpm'])

    @mock.patch('rpm_units_search.pulp_cli._content_command')
    def test_rpm(self, mock_command):
        rpm_units_search.pulp_cli.rpm(a=1, b=2)
        mock_command.assert_called_once_with(
            [rpm_units_search.pulp_cli.TYPE_RPM], a=1, b=2)

    @mock.patch('rpm_units_search.pulp_cli._content_command')
    def test_srpm(self, mock_command):
        rpm_units_search.pulp_cli.srpm(a=1, b=2)
        mock_command.assert_called_once_with(
            [rpm_units_search.pulp_cli.TYPE_SRPM], a=1, b=2)

    @mock.patch('rpm_units_search.pulp_cli._content_command')
    def test_drpm(self, mock_command):
        rpm_units_search.pulp_cli.drpm(a=1, b=2)
        mock_command.assert_called_once_with(
            [rpm_units_search.pulp_cli.TYPE_DRPM], a=1, b=2)

    @mock.patch('rpm_units_search.pulp_cli._content_command')
    def test_package_group(self, mock_command):
        rpm_units_search.pulp_cli.package_group(a=1, b=2)
        mock_command.assert_called_once_with(
            [rpm_units_search.pulp_cli.TYPE_PACKAGE_GROUP], a=1, b=2)

    @mock.patch('rpm_units_search.pulp_cli._content_command')
    def test_package_category(self, mock_command):
        rpm_units_search.pulp_cli.package_category(a=1, b=2)
        mock_command.assert_called_once_with(
            [rpm_units_search.pulp_cli.TYPE_PACKAGE_CATEGORY], a=1, b=2)


class RpmUnitsSearchUtilityTests(rpm_support_base.PulpClientTests):

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

