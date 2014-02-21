# -*- coding: utf-8 -*-
#
# Copyright  © 2013 Red Hat, Inc.
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
from mock import call
from okaara.cli import CommandUsage

from pulp.bindings.exceptions import BadRequestException
from pulp.bindings.bindings import Bindings
from pulp.client.commands import unit
from pulp.client.commands.criteria import UnitAssociationCriteriaCommand
from pulp.client.commands.polling import PollingCommand
from pulp.devel.unit import base, task_simulator


class UnitCopyCommandTests(base.PulpClientTests):

    def setUp(self):
        super(UnitCopyCommandTests, self).setUp()

        self.command = unit.UnitCopyCommand(self.context)

        self.mock_poll = mock.MagicMock().poll
        self.command.poll = self.mock_poll

        self.mock_copy_binding = mock.MagicMock().copy
        self.mock_copy_binding.return_value = task_simulator.create_fake_task_response()
        self.bindings.repo_unit.copy = self.mock_copy_binding

    def test_inherited_functionality(self):
        self.assertTrue(isinstance(self.command, UnitAssociationCriteriaCommand))
        self.assertTrue(isinstance(self.command, PollingCommand))

    def test_structure(self):
        # Ensure all of the expected options are there
        repo_id_options = [o for o in self.command.options if o.keyword == 'repo-id']
        self.assertEqual(0, len(repo_id_options))
        self.assertTrue(unit.OPTION_FROM_REPO in self.command.options)
        self.assertTrue(unit.OPTION_TO_REPO in self.command.options)

        # Ensure the options are configured correctly
        self.assertTrue(unit.OPTION_FROM_REPO.required)
        self.assertTrue(unit.OPTION_TO_REPO.required)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'copy')
        self.assertEqual(self.command.description, unit.DESC_COPY)

    def test_run(self):
        # Setup
        self.cli.add_command(self.command)

        # Test
        self.cli.run('copy --from-repo-id from --to-repo-id to --str-eq name=foo'.split())

        # Verify
        #   Call to the binding with the data collected by the command
        self.assertEqual(1, self.mock_copy_binding.call_count)
        args = self.mock_copy_binding.call_args[0]
        self.assertEqual(args[0], 'from')
        self.assertEqual(args[1], 'to')
        kwargs = self.mock_copy_binding.call_args[1]
        self.assertEqual(kwargs['override_config'], {})  # default for generate_override_config
        self.assertEqual(kwargs['str-eq'], [['name', 'foo']])
        self.assertTrue('type_ids' not in kwargs)

        #   Poll call made with the correct value
        self.assertEqual(1, self.mock_poll.call_count)
        self.assertEqual(self.mock_poll.call_args[0][0],
                         [self.mock_copy_binding.return_value.response_body])

    def test_run_with_type_id(self):
        # Setup
        self.command.type_id = 'fake-type'
        self.cli.add_command(self.command)

        # Test
        self.cli.run('copy --from-repo-id from --to-repo-id to'.split())

        # Verify
        kwargs = self.mock_copy_binding.call_args[1]
        self.assertTrue(kwargs['type_ids'], ['fake-type'])

    def test_run_bad_request(self):
        """
        Tests the property name translation from the REST API keys to the CLI keys.
        """
        # Setup
        self.cli.add_command(self.command)
        self.mock_copy_binding.side_effect = BadRequestException({'property_names':
                                                                  ['source_repo_id']})

        # Test
        try:
            self.cli.run('copy --from-repo-id from --to-repo-id to'.split())
        except BadRequestException, e:
            self.assertEqual(e.extra_data['property_names'], ['from-repo-id'])


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
            {'_id': 'foo', 'id': 'foo', '_content_type_id': 'rpm'})
        self.assertEqual(mock_render.call_count, 2)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document')
    @mock.patch('pulp.bindings.content.OrphanContentAPI.orphans_by_type')
    def test_with_type(self, mock_orphans, mock_render):
        mock_orphans.return_value.response_body =\
            [{'_id': 'foo', '_content_type_id': 'rpm'}]

        self.command.run(**{'type': 'foo', 'details': True})

        mock_orphans.assert_called_once_with('foo')
        mock_render.assert_any_call(
            {'_id': 'foo', 'id': 'foo', '_content_type_id': 'rpm'})
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
        self.assertEqual(last_call_arg, {'rpm': 2, 'srpm': 1, 'Total': 3})


class TestRemove(base.PulpClientTests):
    def setUp(self):
        super(TestRemove, self).setUp()
        self.command = unit.OrphanUnitRemoveCommand(self.context)

    def test_options(self):
        names = set([opt.name for opt in self.command.options])
        self.assertEqual(set(('--bg', '--type', '--unit-id', '--all')), names)

    @mock.patch('pulp.bindings.content.OrphanContentAPI.remove')
    @mock.patch('pulp.client.commands.unit.OrphanUnitRemoveCommand.poll')
    def test_single_unit(self, mock_poll, mock_remove):
        self.command.run(**{'type': 'rpm', 'unit-id': 'foo'})

        mock_remove.assert_called_once_with('rpm', 'foo')
        mock_poll.assert_called_once_with(
            mock_remove.return_value.response_body, mock.ANY)

    @mock.patch('pulp.bindings.content.OrphanContentAPI.remove_by_type')
    @mock.patch('pulp.client.commands.unit.OrphanUnitRemoveCommand.poll')
    def test_type(self, mock_poll, mock_remove):
        self.command.run(type='rpm')

        mock_remove.assert_called_once_with('rpm')
        mock_poll.assert_called_once_with(
            mock_remove.return_value.response_body, mock.ANY)

    @mock.patch('pulp.bindings.content.OrphanContentAPI.remove_all')
    @mock.patch('pulp.client.commands.unit.OrphanUnitRemoveCommand.poll')
    def test_all(self, mock_poll, mock_remove):
        self.command.run(all=True)
        mock_remove.assert_called_once_with()
        mock_poll.assert_called_once_with(
            mock_remove.return_value.response_body, mock.ANY)

    def test_no_options(self):
        self.assertRaises(CommandUsage, self.command.run)

    def test_missing_type(self):
        self.assertRaises(CommandUsage, self.command.run, **{'unit-id': 'foo'})


class TaskResult(object):
    def __init__(self, success, failure):
        self.result = {
            'units_successful': success,
            'units_failed': failure
        }


class TestUnitRemoveCommand(base.PulpClientTests):

    def setUp(self):
        super(TestUnitRemoveCommand, self).setUp()
        self.command = unit.UnitRemoveCommand(self.context)

    def test_formatter_not_implemented_error(self):
        self.assertRaises(NotImplementedError, self.command.get_formatter_for_type, 'foo')

    def test_succeeded_calls_display_task_results(self):
        self.command.display_task_results = mock.Mock()
        self.command.succeeded('foo')
        self.command.display_task_results.assert_called_with('foo',
                                                             unit.RETURN_REMOVE_SUCCESS_STRING,
                                                             unit.RETURN_REMOVE_ERROR_STRING)

    def test_display_task_results_no_values(self):
        self.command.display_task_results(TaskResult([], []), 'success', 'error')

        self.assertEqual(['too-few'], self.prompt.get_write_tags())

    def test_display_task_results_errors(self):
        self.command._details = mock.Mock()
        self.command.display_task_results(TaskResult([], ['error']), 'success', 'error')

        self.assertTrue(self.command._details.called)
        self.assertEqual(['none'], self.prompt.get_write_tags())

    def test_display_task_results_errors_and_values(self):
        self.command._details = mock.Mock()
        self.command.display_task_results(TaskResult(['value'], ['error']), 'success', 'error')

        self.assertTrue(self.command._details.called)
        self.assertEquals(self.command._details.call_count, 2)
        self.assertEqual([], self.prompt.get_write_tags())

    def test_display_task_results_max_units_triggers_summary_view_success(self):
        self.command._summary = mock.Mock()
        self.command.max_units_displayed = 1
        self.command.display_task_results(TaskResult(['foo', 'bar'], []), 'success', 'error')
        self.assertTrue(self.command._summary.called)
        self.assertEqual([], self.prompt.get_write_tags())

    def test_display_task_results_max_units_triggers_summary_view_error(self):
        self.command._summary = mock.Mock()
        self.command.max_units_displayed = 1
        self.command.display_task_results(TaskResult([], ['foo', 'bar']), 'success', 'error')
        self.assertTrue(self.command._summary.called)
        self.assertEqual(['none'], self.prompt.get_write_tags())

    def test_summary(self):
        writer = mock.Mock()
        expected = [call('  a: 2'),
                    call('  b: 1')]
        self.command._summary(writer, [{'type_id': 'a', 'b': 'c'},
                                       {'type_id': 'a', 'b': 'c'},
                                       {'type_id': 'b', 'b': 'c'}])
        self.assertEquals(writer.call_args_list, expected)

    def test_details_single_unit_type(self):
        writer = mock.Mock()
        expected = [call('  c'),
                    call('  d')]
        self.command.get_formatter_for_type = lambda x: lambda y: y['b']
        self.command._details(writer, [{'type_id': 'a', 'unit_key': {'b': 'c'}},
                                       {'type_id': 'a', 'unit_key': {'b': 'd'}}])
        self.assertEquals(writer.call_args_list, expected)

    def test_details_multiple_unit_type(self):
        writer = mock.Mock()
        expected = [call(' alpha:'),
                    call('  c'),
                    call('  d'),
                    call(' bravo:'),
                    call('  e'),
                    call('  f')]
        self.command.get_formatter_for_type = lambda x: lambda y: y['b']
        self.command._details(writer, [{'type_id': 'alpha', 'unit_key': {'b': 'c'}},
                                       {'type_id': 'alpha', 'unit_key': {'b': 'd'}},
                                       {'type_id': 'bravo', 'unit_key': {'b': 'e'}},
                                       {'type_id': 'bravo', 'unit_key': {'b': 'f'}}])
        self.assertEquals(writer.call_args_list, expected)
