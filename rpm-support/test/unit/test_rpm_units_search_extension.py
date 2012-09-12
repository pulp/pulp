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

import rpm_units_search.pulp_cli

class TestUnitSection(unittest.TestCase):
    def setUp(self):
        rpm_units_search.pulp_cli.CONTEXT = mock.MagicMock()

    def test_content_command(self):
        # setup
        return_value = mock.MagicMock()
        return_value.response_body = [{'name':'foo', 'metadata':'unit1'}]
        rpm_units_search.pulp_cli.CONTEXT.server.repo_unit.search.return_value = return_value

        rpm_units_search.pulp_cli._content_command(['rpm'], **{'repo-id': 'repo1'})
        rpm_units_search.pulp_cli.CONTEXT.server.repo_unit.search.assert_called_once_with('repo1', type_ids=['rpm'])
        rpm_units_search.pulp_cli.CONTEXT.prompt.render_document.assert_called_once_with('unit1')

    def test_content_command_metadata(self):
        return_value = mock.MagicMock()
        return_value.response_body = [{'name':'foo', 'metadata':'unit1'}]
        rpm_units_search.pulp_cli.CONTEXT.server.repo_unit.search.return_value = return_value

        rpm_units_search.pulp_cli._content_command(['rpm'], **{'repo-id': 'repo1', 'metadata': True})
        rpm_units_search.pulp_cli.CONTEXT.server.repo_unit.search.assert_called_once_with('repo1', type_ids=['rpm'], metadata=True)
        rpm_units_search.pulp_cli.CONTEXT.prompt.render_document.assert_called_once_with(return_value.response_body[0])

    def test_content_command_out_func(self):
        out = mock.MagicMock()
        return_value = mock.MagicMock()
        return_value.response_body = [{'name':'foo', 'metadata':'unit1'}]
        rpm_units_search.pulp_cli.CONTEXT.server.repo_unit.search.return_value = return_value

        rpm_units_search.pulp_cli._content_command(['rpm'], out, **{'repo-id': 'repo1'})

        # make sure the custom out function was called with the fake document
        self.assertEqual(
            rpm_units_search.pulp_cli.CONTEXT.prompt.render_document.call_count, 0)
        out.assert_called_once_with('unit1')

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

    @mock.patch('rpm_units_search.pulp_cli._content_command')
    def test_distro(self, mock_command):
        rpm_units_search.pulp_cli.distribution(a=1, b=2)
        mock_command.assert_called_once_with(
            [rpm_units_search.pulp_cli.TYPE_DISTRIBUTION],
            rpm_units_search.pulp_cli.write_distro, a=1, b=2)

    @mock.patch('rpm_units_search.pulp_cli._content_command')
    def test_erratum_detail(self, mock_command):
        kwargs = {
            'erratum-id' : 'abc',
            'repo-id' : 'repo1',
            'a' : 1,
            'b' : 2
        }

        # we expect it to throw away other parameters and just search for this
        # specific erratum
        EXPECTED = {
            'filters' : {'id' : 'abc'},
            'repo-id' : 'repo1',
        }
        rpm_units_search.pulp_cli.errata(**kwargs)

        mock_command.assert_called_once_with(
            [rpm_units_search.pulp_cli.TYPE_ERRATUM],
            rpm_units_search.pulp_cli.write_erratum_detail, **EXPECTED)

    @mock.patch('rpm_units_search.pulp_cli._content_command')
    def test_errata(self, mock_command):
        kwargs = {
            'erratum-id' : None,
            'repo-id' : 'repo1',
            'a' : 1,
            'b' : 2
        }
        rpm_units_search.pulp_cli.errata(**kwargs)

        # we expect this to pass through any CLI options
        mock_command.assert_called_once_with(
            [rpm_units_search.pulp_cli.TYPE_ERRATUM],
            rpm_units_search.pulp_cli.write_erratum, **kwargs)

    def test_write_distro(self):
        rpm_units_search.pulp_cli.write_distro(mock.MagicMock())
        # again, there is so much going on, let's just verify the basics
        self.assertTrue(rpm_units_search.pulp_cli.CONTEXT.prompt.write.has_calls)

    def test_write_erratum(self):
        rpm_units_search.pulp_cli.write_erratum({'metadata': 'foo'})
        rpm_units_search.pulp_cli.CONTEXT.prompt.render_document.assert_called_once_with('foo')

    def test_write_erratum_detail(self):
        rpm_units_search.pulp_cli.write_erratum_detail(mock.MagicMock())

        # Where to begin!?!? Let's just cover the basics.
        self.assertEqual(
            rpm_units_search.pulp_cli.CONTEXT.prompt.render_title.call_count, 1)
        self.assertEqual(
            rpm_units_search.pulp_cli.CONTEXT.prompt.write.call_count, 1)
