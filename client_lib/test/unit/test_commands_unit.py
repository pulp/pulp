#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2012-2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import mock
from okaara.cli import CommandUsage

from pulp.bindings.bindings import Bindings
from pulp.client.commands import unit
from pulp.devel.unit import base


def create_bindings():
    mock_context = mock.MagicMock()
    mock_context.server = Bindings(mock.MagicMock())
    return mock_context


class TestList(base.PulpClientTests):
    def setUp(self):
        super(TestList, self).setUp()
        self.command = unit.OrphanUnitListCommand(self.context)

    def test_option(self):
        # options are --type and --summary
        self.assertEqual(len(self.command.options), 2)
        self.assertEqual('--type', self.command.options[0].name)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document')
    @mock.patch('pulp.bindings.content.OrphanContentAPI.orphans_by_type')
    def test_all(self, mock_orphans_by_type, mock_render):
        mock_orphans_by_type.return_value.response_body =\
            [{'_id': 'foo', '_content_type_id': 'rpm'}]

        self.command.run(type='rpm', details=True)

        mock_orphans_by_type.assert_called_once_with('rpm')
        mock_render.assert_any_call(
            {'_id' : 'foo', 'id' : 'foo', '_content_type_id': 'rpm'})
        self.assertEqual(mock_render.call_count, 2)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document')
    @mock.patch('pulp.bindings.content.OrphanContentAPI.orphans_by_type')
    def test_with_type(self, mock_orphans, mock_render):
        mock_orphans.return_value.response_body =\
            [{'_id': 'foo', '_content_type_id': 'rpm'}]

        self.command.run(**{'type' : 'foo', 'details': True})

        mock_orphans.assert_called_once_with('foo')
        mock_render.assert_any_call(
                {'_id' : 'foo', 'id' : 'foo', '_content_type_id': 'rpm'})
        self.assertEqual(mock_render.call_count, 2)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document')
    @mock.patch('pulp.bindings.content.OrphanContentAPI.orphans')
    def test_summary(self, mock_orphans, mock_render):
        mock_orphans.return_value.response_body = {
            'rpm': {'count': 2, '_href': 'whocares'},
            'srpm': {'count': 1, '_href': 'stillwhocares'},
        }

        self.command.run()

        last_call_arg = mock_render.call_args[0][0]
        self.assertEqual(last_call_arg, {'rpm':2, 'srpm':1, 'Total':3})


class TestRemove(base.PulpClientTests):
    def setUp(self):
        super(TestRemove, self).setUp()
        self.command = unit.OrphanUnitRemoveCommand(self.context)

    def test_options(self):
        names = set([opt.name for opt in self.command.options])
        self.assertEqual(set(('--type', '--unit-id', '--all')), names)

    @mock.patch('pulp.bindings.content.OrphanContentAPI.remove')
    @mock.patch('pulp.client.commands.unit.OrphanUnitRemoveCommand.check_task_status')
    def test_single_unit(self, mock_check_status, mock_remove):
        self.command.run(**{'type': 'rpm', 'unit-id': 'foo'})

        mock_remove.assert_called_once_with('rpm', 'foo')
        mock_check_status.assert_called_once_with(
            mock_remove.return_value.response_body)

    @mock.patch('pulp.bindings.content.OrphanContentAPI.remove_by_type')
    @mock.patch('pulp.client.commands.unit.OrphanUnitRemoveCommand.check_task_status')
    def test_type(self, mock_check_status, mock_remove):
        self.command.run(type='rpm')

        mock_remove.assert_called_once_with('rpm')
        mock_check_status.assert_called_once_with(
            mock_remove.return_value.response_body)


    @mock.patch('pulp.bindings.content.OrphanContentAPI.remove_all')
    @mock.patch('pulp.client.commands.unit.OrphanUnitRemoveCommand.check_task_status')
    def test_all(self, mock_check_status, mock_remove):
        self.command.run(all=True)
        mock_remove.assert_called_once_with()
        mock_check_status.assert_called_once_with(
            mock_remove.return_value.response_body)

    def test_no_options(self):
        self.assertRaises(CommandUsage, self.command.run)

    def test_missing_type(self):
        self.assertRaises(CommandUsage, self.command.run, **{'unit-id':'foo'})

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_reasons')
    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_failure_message')
    def test_check_status_rejected(self, mock_failure, mock_reasons):
        mock_response = mock.MagicMock()
        mock_response.response = 'rejected'
        mock_response.reasons = ['foo']

        self.command.check_task_status(mock_response)

        self.assertEqual(mock_failure.call_count, 1)
        mock_reasons.assert_called_once_with(['foo'])

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_success_message')
    def test_check_status_ok(self, mock_success):
        mock_response = mock.MagicMock()
        mock_response.response = 'accepted'

        self.command.check_task_status(mock_response)

        self.assertEqual(mock_success.call_count, 1)
