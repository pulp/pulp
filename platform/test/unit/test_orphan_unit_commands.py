#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

import mock
from okaara.cli import CommandUsage

from pulp.bindings.bindings import Bindings
from pulp.client.commands import unit


def create_bindings():
    mock_context = mock.MagicMock()
    mock_context.server = Bindings(mock.MagicMock())
    return mock_context


class TestList(unittest.TestCase):
    def setUp(self):
        self.command = unit.OrphanUnitListCommand(create_bindings())

    def test_option(self):
        self.assertEqual(len(self.command.options), 1)
        self.assertEqual('--type', self.command.options[0].name)

    @mock.patch('pulp.bindings.content.OrphanContentAPI.orphans')
    def test_all(self, mock_orphans):
        mock_orphans.return_value.response_body = [{'_id': 'foo'}]

        self.command.run()

        mock_orphans.assert_called_once_with()
        self.command.context.prompt.render_document.assert_called_once_with(
            {'_id' : 'foo', 'id' : 'foo'})

    @mock.patch('pulp.bindings.content.OrphanContentAPI.orphans_by_type')
    def test_with_type(self, mock_orphans):
        mock_orphans.return_value.response_body = [{'_id': 'foo'}]

        self.command.run(**{'type' : 'foo'})

        mock_orphans.assert_called_once_with('foo')
        self.command.context.prompt.render_document.assert_called_once_with(
                {'_id' : 'foo', 'id' : 'foo'})


class TestRemove(unittest.TestCase):
    def setUp(self):
        self.command = unit.OrphanUnitRemoveCommand(create_bindings())

    def test_options(self):
        names = set([opt.name for opt in self.command.options])
        self.assertEqual(set(('--type', '--unit-id', '--all')), names)

    @mock.patch('pulp.bindings.content.OrphanContentAPI.remove')
    @mock.patch.object(unit, 'check_task_status')
    def test_single_unit(self, mock_check_status, mock_remove):
        self.command.run(**{'type': 'rpm', 'unit-id': 'foo'})

        mock_remove.assert_called_once_with('rpm', 'foo')
        mock_check_status.assert_called_once_with(
            mock_remove.return_value.response_body, self.command.context.prompt)

    @mock.patch('pulp.bindings.content.OrphanContentAPI.remove_by_type')
    @mock.patch.object(unit, 'check_task_status')
    def test_type(self, mock_check_status, mock_remove):
        self.command.run(type='rpm')

        mock_remove.assert_called_once_with('rpm')
        mock_check_status.assert_called_once_with(
            mock_remove.return_value.response_body, self.command.context.prompt)


    @mock.patch('pulp.bindings.content.OrphanContentAPI.remove_all')
    @mock.patch.object(unit, 'check_task_status')
    def test_all(self, mock_check_status, mock_remove):
        self.command.run(all=True)
        mock_remove.assert_called_once_with()
        mock_check_status.assert_called_once_with(
            mock_remove.return_value.response_body, self.command.context.prompt)

    def test_no_options(self):
        self.assertRaises(CommandUsage, self.command.run)

    def test_missing_type(self):
        self.assertRaises(CommandUsage, self.command.run, **{'unit-id':'foo'})

    def test_check_status_rejected(self):
        mock_response = mock.MagicMock()
        mock_response.response = 'rejected'
        mock_response.reasons = ['foo']

        self.command.check_task_status(mock_response)

        self.assertEqual(self.command.context.prompt.render_failure_message.call_count, 1)
        self.command.context.prompt.render_reasons.assert_called_once_with(['foo'])

    def test_check_status_ok(self):
        mock_response = mock.MagicMock()
        mock_response.response = 'accepted'

        self.command.check_task_status(mock_response)

        self.assertEqual(self.command.context.prompt.render_success_message.call_count, 1)
