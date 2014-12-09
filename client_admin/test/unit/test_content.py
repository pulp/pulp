from unittest import TestCase

from mock import Mock, patch, MagicMock

from pulp.bindings import responses

from pulp.client.admin.content import (initialize, MainSection, SourcesSection, ListCommand,
                                       CatalogDeleteCommand, RefreshContentSourcesCommand)
from pulp.common.plugins import reporting_constants
from pulp.client.commands import options
from pulp.client.commands.repo.status import PublishStepStatusRenderer
from pulp.devel.unit import base


class TestInitialization(TestCase):

    @patch('pulp.client.admin.content.MainSection')
    def test_init(self, main_section):
        context = Mock()

        # test
        initialize(context)

        # validation
        main_section.assert_called_once_with(context)
        context.cli.add_section.assert_called_once_with(main_section.return_value)


class TestMainSection(TestCase):

    @patch('pulp.client.admin.content.SourcesSection')
    @patch('pulp.client.admin.content.MainSection.add_subsection')
    def test_init(self, add_subsection, sources_section):
        context = Mock()

        # test
        MainSection(context)

        # validation
        sources_section.assert_called_once_with(context)
        add_subsection.assert_any_with(sources_section.return_value)


class TestSourcesSection(TestCase):

    @patch('pulp.client.admin.content.RefreshContentSourcesCommand')
    @patch('pulp.client.admin.content.ListCommand')
    @patch('pulp.client.admin.content.SourcesSection.add_command')
    def test_init(self, add_command, list_command, refresh_command):
        context = Mock(config={'output': {'poll_frequency_in_seconds': 1}})

        # test
        SourcesSection(context)

        # validationfrom pulp.common.plugins import reporting_constants

        list_command.assert_called_once_with(context)
        add_command.assert_has_calls(list_command.return_value, refresh_command)


class TestCatalogSection(TestCase):

    @patch('pulp.client.admin.content.CatalogSection')
    @patch('pulp.client.admin.content.MainSection.add_subsection')
    def test_init(self, add_subsection, catalog_section):
        context = Mock(config={'output': {'poll_frequency_in_seconds': 1}})

        # test
        MainSection(context)

        # validation
        catalog_section.assert_called_once_with(context)
        add_subsection.assert_any_with(catalog_section.return_value)


class TestListCommand(TestCase):

    def test_run(self):
        context = Mock()
        response = Mock(response_code=200, response_body=[1, 2, 3])
        context.server.content_source.get_all.return_value = response

        # test
        command = ListCommand(context)
        command._run()

        # validation
        context.prompt.render_title.assert_called_once_with(ListCommand.TITLE)
        context.server.content_source.get_all.assert_called_once_with()
        context.prompt.render_document_list.assert_called_once_with(response.response_body)


class TestCatalogDeleteCommand(TestCase):

    def test_run(self):
        source_id = 'content-world'
        context = Mock()
        response = Mock(response_code=200, response_body={'deleted': 10})
        context.server.content_catalog.delete.return_value = response

        # test
        command = CatalogDeleteCommand(context)
        kwargs = {CatalogDeleteCommand.SOURCE_ID_OPTION.keyword: source_id}
        command._run(**kwargs)

        # validation
        msg = 'Successfully deleted [10] catalog entries.'
        context.server.content_catalog.delete.assert_called_once_with(source_id)
        context.prompt.render_success_message.assert_called_once_with(msg)

    def test_run_nothing_matched(self):
        source_id = 'content-world'
        context = Mock()
        response = Mock(response_code=200, response_body={'deleted': 0})
        context.server.content_catalog.delete.return_value = response

        # test
        command = CatalogDeleteCommand(context)
        kwargs = {CatalogDeleteCommand.SOURCE_ID_OPTION.keyword: source_id}
        command._run(**kwargs)

        # validation
        msg = 'No catalog entries matched.'
        context.server.content_catalog.delete.assert_called_once_with(source_id)
        context.prompt.render_success_message.assert_called_once_with(msg)


class TestRefreshContentSourcesCommand(base.PulpClientTests):
    def setUp(self):
        super(TestRefreshContentSourcesCommand, self).setUp()
        self.context = MagicMock(config={'output': {'poll_frequency_in_seconds': 1}})
        self.prompt = Mock()
        self.context.prompt = self.prompt
        self.renderer = PublishStepStatusRenderer(self.context)
        self.command = RefreshContentSourcesCommand(self.context, self.renderer)
        step_details = {'source_id': '1',
                        'succeeded': None,
                        'url': 'mock-url',
                        'added_count': '2',
                        'deleted_count': '0',
                        'errors': []
                        }
        self.step = {
            reporting_constants.PROGRESS_STEP_TYPE_KEY: u'foo_step',
            reporting_constants.PROGRESS_STEP_UUID: u'abcde',
            reporting_constants.PROGRESS_DESCRIPTION_KEY: u'foo description',
            reporting_constants.PROGRESS_DETAILS_KEY: [step_details],
            reporting_constants.PROGRESS_STATE_KEY: reporting_constants.STATE_NOT_STARTED,
            reporting_constants.PROGRESS_ITEMS_TOTAL_KEY: 1,
            reporting_constants.PROGRESS_NUM_PROCESSED_KEY: 0,
            reporting_constants.PROGRESS_ERROR_DETAILS_KEY: []
        }

    @patch('pulp.client.commands.polling.PollingCommand.poll')
    def test_run_one(self, mock_poll):
        """
        Test run() when there are no refresh content source tasks on the server.
        """
        content_source_id = 'test-content'
        data = {options.OPTION_CONTENT_SOURCE_ID.keyword: content_source_id}
        # No tasks are running
        self.command.run(**data)
        self.assertEqual(1, mock_poll.call_count)

    @patch('pulp.client.commands.polling.PollingCommand.poll')
    def test_run_all(self, mock_poll):
        """
        Test run() when there are no refresh content source tasks on the server.
        """
        data = {options.OPTION_CONTENT_SOURCE_ID.keyword: None}
        # No tasks are running
        self.command.run(**data)
        self.assertEqual(1, mock_poll.call_count)

    def test_progress(self):
        """
        Test the progress() method with a progress_report.
        """
        task = responses.Task({'progress_report': {'Refresh Content Sources': self.step}})
        spinner = MagicMock()
        self.renderer.display_report = MagicMock()
        self.command.progress(task, spinner)

        self.renderer.display_report.assert_called_once_with({'Refresh Content Sources': self.step})
