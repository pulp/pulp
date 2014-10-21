from unittest import TestCase

from mock import Mock, patch

from pulp.client.admin.content import initialize, MainSection, SourcesSection, ListCommand


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
        add_subsection.assert_called_once_with(sources_section.return_value)


class TestSourcesSection(TestCase):

    @patch('pulp.client.admin.content.ListCommand')
    @patch('pulp.client.admin.content.SourcesSection.add_command')
    def test_init(self, add_command, list_command):
        context = Mock()

        # test
        SourcesSection(context)

        # validation
        list_command.assert_called_once_with(context)
        add_command.assert_called_once_with(list_command.return_value)


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
