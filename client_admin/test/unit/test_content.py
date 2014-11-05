from unittest import TestCase

from mock import Mock, patch

from pulp.client.admin.content import (initialize, MainSection, SourcesSection,
    ListCommand, CatalogDeleteCommand)


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

    @patch('pulp.client.admin.content.ListCommand')
    @patch('pulp.client.admin.content.SourcesSection.add_command')
    def test_init(self, add_command, list_command):
        context = Mock()

        # test
        SourcesSection(context)

        # validation
        list_command.assert_called_once_with(context)
        add_command.assert_called_once_with(list_command.return_value)


class TestCatalogSection(TestCase):

    @patch('pulp.client.admin.content.CatalogSection')
    @patch('pulp.client.admin.content.MainSection.add_subsection')
    def test_init(self, add_subsection, catalog_section):
        context = Mock()

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
