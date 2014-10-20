from gettext import gettext as _
from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand


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
