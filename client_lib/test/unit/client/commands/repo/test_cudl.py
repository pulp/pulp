import mock

from pulp.common import tags
from pulp.devel.unit.util import compare_dict
from pulp.bindings.responses import STATE_FINISHED, Task
from pulp.client.commands.polling import PollingCommand, FLAG_BACKGROUND
from pulp.client.commands.repo import cudl
from pulp.client.commands.options import OPTION_DESCRIPTION, OPTION_NAME, OPTION_NOTES, OPTION_REPO_ID
from pulp.client.extensions.core import TAG_SUCCESS, TAG_TITLE
from pulp.common.compat import json
from pulp.devel.unit import base
from pulp.devel.unit.task_simulator import TaskSimulator


class CreateRepositoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(CreateRepositoryCommandTests, self).setUp()
        self.command = cudl.CreateRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure all of the expected options are there
        for o in [OPTION_DESCRIPTION, OPTION_NAME, OPTION_NOTES, OPTION_REPO_ID]:
            self.assertIn(o, self.command.options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'create')
        self.assertEqual(self.command.description, cudl.DESC_CREATE)

    def test_run(self):
        # Setup
        data = {
            OPTION_REPO_ID.keyword: 'test-repo',
            OPTION_NAME.keyword: 'Test Repository',
            OPTION_DESCRIPTION.keyword: 'Repository Description',
            OPTION_NOTES.keyword: ['a=a', 'b=b'],
        }
        self.command.default_notes = {'foo': 'bar'}

        self.server_mock.request.return_value = 201, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('POST', self.server_mock.request.call_args[0][0])

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)
        self.assertEqual(body['id'], 'test-repo')
        self.assertEqual(body['display_name'], 'Test Repository')
        self.assertEqual(body['description'], 'Repository Description')
        self.assertEqual(body['notes'], {'a': 'a', 'b': 'b', 'foo': 'bar'})

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])

    def test_parse_basic_options_default_notes(self):
        data = {
            OPTION_REPO_ID.keyword: 'test-repo',
            OPTION_NAME.keyword: 'Test Repository',
            OPTION_DESCRIPTION.keyword: 'Repository Description',
            OPTION_NOTES.keyword: [],
        }
        repo_id, name, description, notes = self.command._parse_basic_options(data)

        self.assertEqual(notes, {})


class CreateAndConfigureRepositoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(CreateAndConfigureRepositoryCommandTests, self).setUp()
        self.command = cudl.CreateAndConfigureRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure all of the expected options are there
        for o in [OPTION_DESCRIPTION, OPTION_NAME, OPTION_NOTES, OPTION_REPO_ID]:
            self.assertIn(o, self.command.options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'create')
        self.assertEqual(self.command.description, cudl.DESC_CREATE)

    def test_run(self):
        # Setup
        data = {
            OPTION_REPO_ID.keyword: 'test-repo',
            OPTION_NAME.keyword: 'Test Repository',
            OPTION_DESCRIPTION.keyword: 'Repository Description',
            OPTION_NOTES.keyword: ['a=a', 'b=b'],
        }
        self.command.default_notes = {'foo': 'bar'}

        self.server_mock.request.return_value = 201, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('POST', self.server_mock.request.call_args[0][0])

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)
        self.assertEqual(body['id'], 'test-repo')
        self.assertEqual(body['display_name'], 'Test Repository')
        self.assertEqual(body['description'], 'Repository Description')
        self.assertEqual(body['notes'], {'a': 'a', 'b': 'b', 'foo': 'bar'})
        self.assertEqual(body['distributors'], [])
        self.assertEqual(body['importer_type_id'], None)

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])


class DeleteRepositoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(DeleteRepositoryCommandTests, self).setUp()
        self.command = cudl.DeleteRepositoryCommand(self.context)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, PollingCommand))

        # Ensure all of the expected options are there
        self.assertIn(OPTION_REPO_ID, self.command.options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'delete')
        self.assertEqual(self.command.description, cudl.DESC_DELETE)

    @mock.patch('pulp.client.commands.polling.PollingCommand.poll')
    def test_run(self, mock_poll):
        # Setup
        data = {
            OPTION_REPO_ID.keyword: 'test-repo',
        }

        sim = TaskSimulator()
        sim.add_task_state('123', STATE_FINISHED)

        mock_binding_delete = mock.MagicMock().delete
        mock_binding_delete.return_value = sim.get_all_tasks()
        self.bindings.repo.delete = mock_binding_delete

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, mock_binding_delete.call_count)
        self.assertEqual('test-repo', mock_binding_delete.call_args[0][0])
        self.assertEqual(1, mock_poll.call_count)

    def test_run_not_found(self):
        # Setup
        data = {
            OPTION_REPO_ID.keyword: 'test-repo',
        }

        self.server_mock.request.return_value = 404, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual('not-found', self.prompt.get_write_tags()[0])


class UpdateRepositoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(UpdateRepositoryCommandTests, self).setUp()
        self.command = cudl.UpdateRepositoryCommand(self.context)

    def test_structure(self):
        # Ensure all of the expected options are there
        found_options = set(self.command.options)
        expected_options = set([OPTION_DESCRIPTION, OPTION_NAME, OPTION_NOTES, OPTION_REPO_ID])
        expected_options.add(FLAG_BACKGROUND)
        self.assertEqual(found_options, expected_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'update')
        self.assertEqual(self.command.description, cudl.DESC_UPDATE)

    def test_task_header_no_tags(self):
        task = Task({})
        task.tags = []

        self.command.task_header(task)

        self.assertEqual(self.prompt.get_write_tags(), [])

    def test_task_header_unrelated_tags(self):
        task = Task({})
        task.tags = ['foo', 'bar']

        self.command.task_header(task)

        self.assertEqual(self.prompt.get_write_tags(), [])

    def test_task_header_action_tag_only(self):
        task = Task({})
        task.tags = [tags.action_tag(tags.ACTION_UPDATE_DISTRIBUTOR)]

        self.command.task_header(task)

        self.assertEqual(self.prompt.get_write_tags(), [tags.ACTION_UPDATE_DISTRIBUTOR])

    def test_task_header_with_dist_tags(self):
        task = Task({})
        task.tags = [
            tags.action_tag(tags.ACTION_UPDATE_DISTRIBUTOR),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, 'some_distributor'),
        ]

        self.command.task_header(task)

        self.assertEqual(self.prompt.get_write_tags(), [tags.ACTION_UPDATE_DISTRIBUTOR])
        # the message in this case should end with the distributor type
        self.assertTrue(self.recorder.lines[0].strip().endswith('some_distributor'))

    def test_run(self):
        # Setup
        repo_id = 'test-repo'
        data = {
            OPTION_REPO_ID.keyword: repo_id,
            OPTION_NAME.keyword: 'Test Repository',
            OPTION_DESCRIPTION.keyword: 'Repository Description',
            OPTION_NOTES.keyword: {'a': 'a', 'b': 'b'},
            'distributor_configs': {'alpha': {'beta': 'gamma'}},
            'importer_config': {'delta': 'epsilon'}
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('PUT', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertTrue(url.endswith('/repositories/%s/' % repo_id))

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        body_target = {
            'delta': {
                'display_name': 'Test Repository',
                'description': 'Repository Description',
                'notes': {'a': 'a', 'b': 'b'}
            },
            'distributor_configs': {'alpha': {'beta': 'gamma'}},
            'importer_config': {'delta': 'epsilon'}

        }
        compare_dict(body, body_target)

        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual(TAG_SUCCESS, self.prompt.get_write_tags()[0])

    def test_run_async(self):
        # Setup
        repo_id = 'test-repo'
        data = {
            OPTION_REPO_ID.keyword: repo_id,
            OPTION_NAME.keyword: 'Test Repository',
            OPTION_DESCRIPTION.keyword: 'Repository Description',
            OPTION_NOTES.keyword: {'a': 'a', 'b': 'b'},
            'distributor_configs': {'alpha': {'beta': 'gamma'}},
            'importer_config': {'delta': 'epsilon'}
        }

        result_task = Task({})
        self.server_mock.request.return_value = 200, result_task
        self.command.poll = mock.Mock()

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('PUT', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertTrue(url.endswith('/repositories/%s/' % repo_id))

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        body_target = {
            'delta': {
                'display_name': 'Test Repository',
                'description': 'Repository Description',
                'notes': {'a': 'a', 'b': 'b'}
            },
            'distributor_configs': {'alpha': {'beta': 'gamma'}},
            'importer_config': {'delta': 'epsilon'}

        }
        compare_dict(body, body_target)

        self.command.poll.assert_called_once_with([result_task], mock.ANY)

    def test_run_not_found(self):
        # Setup
        data = {
            OPTION_REPO_ID.keyword: 'test-repo',
        }

        self.server_mock.request.return_value = 404, {}

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, len(self.prompt.get_write_tags()))
        self.assertEqual('not-found', self.prompt.get_write_tags()[0])


class ListRepositoriesCommandTests(base.PulpClientTests):

    def setUp(self):
        super(ListRepositoriesCommandTests, self).setUp()
        self.command = cudl.ListRepositoriesCommand(self.context)

    def test_structure(self):
        # Ensure the correct arguments are present
        expected_option_names = set(['--details', '--fields', '--all', '--summary', '--repo-id'])
        found_option_names = set([o.name for o in self.command.options])
        self.assertEqual(expected_option_names, found_option_names)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'list')
        self.assertEqual(self.command.description, cudl.DESC_LIST)

    def test_no_all_structure(self):
        # Ensure the all argument isn't present
        self.command = cudl.ListRepositoriesCommand(self.context, include_all_flag=False)
        expected_option_names = set(['--details', '--fields', '--summary', '--repo-id'])
        found_option_names = set([o.name for o in self.command.options])
        self.assertEqual(expected_option_names, found_option_names)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list')
    def test_run_with_details(self, mock_call):
        # Setup
        data = {
            'summary': False,
            'details': True
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('GET', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertIn('/repositories/', url)
        self.assertIn('importers=True', url)
        self.assertIn('distributors=True', url)

        render_kwargs = mock_call.call_args[1]
        expected = ['id', 'display_name', 'description', 'content_unit_counts',
                    'notes', 'importers', 'distributors']
        self.assertEqual(render_kwargs['filters'], expected)
        self.assertEqual(render_kwargs['order'], expected)

        self.assertEqual(1, len(self.prompt.get_write_tags()))  # only one title, not the others

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list')
    def test_run_one_repo_with_details(self, mock_call):
        # Setup
        data = {
            'summary': False,
            'details': True,
            'repo-id': 'zoo-repo'
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.display_repositories(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)
        self.assertEqual('GET', self.server_mock.request.call_args[0][0])

        url = self.server_mock.request.call_args[0][1]
        self.assertIn('/repositories/zoo-repo/', url)
        self.assertIn('importers=True', url)
        self.assertIn('distributors=True', url)

        render_kwargs = mock_call.call_args[1]
        expected = ['id', 'display_name', 'description', 'content_unit_counts',
                    'notes', 'importers', 'distributors']
        self.assertEqual(render_kwargs['filters'], expected)
        self.assertEqual(render_kwargs['order'], expected)

        self.assertEqual(1, len(self.prompt.get_write_tags()))  # only one title, not the others

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list')
    def test_run_with_fields(self, mock_call):
        # Setup
        data = {
            'summary': False,
            'details': False,
            'fields': 'display_name'
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.run(**data)

        # Verify
        render_kwargs = mock_call.call_args[1]
        expected_filters = ['display_name', 'id']

        self.assertEqual(render_kwargs['filters'], expected_filters)
        self.assertEqual(render_kwargs['order'], ['id'])

        self.assertEqual(1, len(self.prompt.get_write_tags()))  # only one title, not the others

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_document_list')
    def test_run_one_repo_with_fields(self, mock_call):
        # Setup
        data = {
            'summary': False,
            'details': False,
            'fields': 'display_name',
            'repo-id': 'zoo-repo'
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.display_repositories(**data)

        # Verify
        url = self.server_mock.request.call_args[0][1]
        self.assertIn('/repositories/zoo-repo/', url)
        render_kwargs = mock_call.call_args[1]
        expected_filters = ['display_name', 'id']

        self.assertEqual(render_kwargs['filters'], expected_filters)
        self.assertEqual(render_kwargs['order'], ['id'])

        self.assertEqual(1, len(self.prompt.get_write_tags()))  # only one title, not the others

    def test_all(self):
        # Setup
        data = {
            'summary': False,
            'details': True,
            'all': True
        }

        self.server_mock.request.return_value = 200, []

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(2, len(self.prompt.get_write_tags()))  # only one title, not the others
        self.assertEqual([TAG_TITLE, TAG_TITLE], self.prompt.get_write_tags())

    def test_summary(self):
        # Setup
        data = {
            'summary': True,
            'details': False
        }

        self.command.get_repositories = mock.MagicMock()
        self.command.get_other_repositories = mock.MagicMock()
        self.command.get_repositories.return_value = [
            {'id': 'abcdef', 'display_name': 'ABCDEF'},
            {'id': 'xyz', 'display_name': 'XYZ'}
        ]

        self.command.prompt.terminal_size = mock.MagicMock()
        self.command.prompt.terminal_size.return_value = 20, 20

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(self.command.get_repositories.call_count, 1)
        self.assertEqual(self.command.get_other_repositories.call_count, 0)

        self.assertEqual(self.recorder.lines[0], 'abcdef  ABCDEF\n')
        self.assertEqual(self.recorder.lines[1], 'xyz     XYZ\n')

    def test_one_repo_summary(self):
        # Setup
        data = {
            'summary': True,
            'details': False,
            'repo-id': 'zoo-repo'
        }

        self.command.get_repository = mock.MagicMock()
        self.command.get_repository.return_value = {
            'id': 'zoo-repo', 'display_name': 'zoo-repo'
        }

        self.command.prompt.terminal_size = mock.MagicMock()
        self.command.prompt.terminal_size.return_value = 20, 20

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(self.command.get_repository.call_count, 1)
        self.assertEqual(self.recorder.lines[0], 'zoo-repo   zoo-repo\n')

    def test_summary_when_empty(self):
        # Test that summmary is an empty list when there are no repositories
        self.command.prompt.terminal_size = mock.MagicMock()
        self.command.prompt.terminal_size.return_value = 20, 20

        repo_list = []
        cudl._default_summary_view(repo_list, self.context.prompt)
        self.assertEqual(len(self.recorder.lines), 0)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_failure_message')
    def test_summary_details_together(self, render_failure_message):
        # Setup
        data = {
            'summary': True,
            'details': True
        }

        # Test
        self.command.run(**data)

        # Verify
        render_failure_message.assert_called_once_with('The summary and details views cannot be used together')
