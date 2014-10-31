from gettext import gettext as _
from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand, PulpCliOption


def initialize(context):
    """
    Initialize the *content* section.
    :param context: The client context.
    :type context: pulp.client.extensions.core.ClientContext
    """
    main = MainSection(context)
    context.cli.add_section(main)


class MainSection(PulpCliSection):
    """
    The *content* main section.
    """

    NAME = 'content'
    DESCRIPTION = _('manage content')

    def __init__(self, context):
        """
        :param context: The client context.
        :type context: pulp.client.extensions.core.ClientContext
        """
        super(MainSection, self).__init__(self.NAME, self.DESCRIPTION)
        self.add_subsection(SourcesSection(context))
        self.add_subsection(CatalogSection(context))


class SourcesSection(PulpCliSection):
    """
    The content *sources* section.
    """

    NAME = 'sources'
    DESCRIPTION = _('manage content sources')

    def __init__(self, context):
        """
        :param context: The client context.
        :type context: pulp.client.extensions.core.ClientContext
        """
        super(SourcesSection, self).__init__(self.NAME, self.DESCRIPTION)
        self.add_command(ListCommand(context))


class CatalogSection(PulpCliSection):
    """
    The content *catalog* section.
    """

    NAME = 'catalog'
    DESCRIPTION = _('manage the content catalog')

    def __init__(self, context):
        """
        :param context: The client context.
        :type context: pulp.client.extensions.core.ClientContext
        """
        super(CatalogSection, self).__init__(self.NAME, self.DESCRIPTION)
        self.add_command(CatalogDeleteCommand(context))


class ListCommand(PulpCliCommand):
    """
    List command.
    :ivar context: The client context.
    :type context: pulp.client.extensions.core.ClientContext
    """

    NAME = 'list'
    DESCRIPTION = _('list sources')
    TITLE = _('Content Sources')

    def __init__(self, context):
        """
        :param context: The client context.
        :type context: pulp.client.extensions.core.ClientContext
        """
        super(ListCommand, self).__init__(self.NAME, self.DESCRIPTION, self._run)
        self.context = context

    def _run(self):
        """
        List content sources.
        """
        self.context.prompt.render_title(self.TITLE)
        response = self.context.server.content_source.get_all()
        self.context.prompt.render_document_list(response.response_body)


class CatalogDeleteCommand(PulpCliCommand):
    """
    Delete catalog entries command.
    :ivar context: The client context.
    :type context: pulp.client.extensions.core.ClientContext
    """

    NAME = 'delete'
    DESCRIPTION = _('delete entries from the catalog')
    SOURCE_ID_OPTION = PulpCliOption('--source-id', _('contributing content source'), aliases='-s')
    DELETED_MSG = _('Successfully deleted [%(deleted)s] catalog entries.')
    NONE_MATCHED_MSG = _('No catalog entries matched.')

    def __init__(self, context):
        """
        :param context: The client context.
        :type context: pulp.client.extensions.core.ClientContext
        """
        super(CatalogDeleteCommand, self).__init__(self.NAME, self.DESCRIPTION, self._run)
        self.add_option(self.SOURCE_ID_OPTION)
        self.context = context

    def _run(self, **kwargs):
        """
        Delete the content catalog for the specified source.
        Supported options:
          - source-id
        :param kwargs: User specified options.
        :type kwargs: dict
        """
        source_id = kwargs[self.SOURCE_ID_OPTION.keyword]
        response = self.context.server.content_catalog.delete(source_id)
        if response.response_body['deleted']:
            self.context.prompt.render_success_message(self.DELETED_MSG % response.response_body)
        else:
            self.context.prompt.render_success_message(self.NONE_MATCHED_MSG)
