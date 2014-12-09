from gettext import gettext as _
from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand, PulpCliOption
from pulp.client.commands import options, polling
from pulp.client.commands.repo.sync_publish import StatusRenderer
from pulp.common.plugins import reporting_constants
from pulp.client.commands.repo.status import PublishStepStatusRenderer


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
        renderer = PublishStepStatusRenderer(context)
        self.add_command(RefreshContentSourcesCommand(context, renderer))


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


class RefreshContentSourcesCommand(polling.PollingCommand):
    """
    Refresh content sources command
    """

    NAME = 'refresh'
    DESCRIPTION = _('refresh sources')
    TITLE = _('Refresh Content Sources')

    def __init__(self, context, renderer, name=NAME, description=DESCRIPTION, method=None):
        """
        Initialize the command, and call the superclass __init__().

        :param name:        The name of the command
        :type  name:        basestring
        :param description: The description of the command
        :type  description: basestring
        :param method:      The method to be run if the command is used
        :type  method:      callable
        :param context:     The CLI context from Okaara
        :type  context:     pulp.client.extensions.core.ClientContext
        :param renderer:    The renderer to be used to print progress reports
        :type  renderer:    StatusRenderer
        """
        if method is None:
            method = self.run

        super(RefreshContentSourcesCommand, self).__init__(name, description, method, context)
        self.add_option(options.OPTION_CONTENT_SOURCE_ID)
        self.add_flag(options.FLAG_ALL)
        self.renderer = renderer
        self.context = context
        self.prompt = context.prompt

    def progress(self, task, spinner):
        """
        Render the progress report, if it is available on the given task.

        :param task:    The Task that we wish to render progress about
        :type  task:    pulp.bindings.responses.Task
        :param spinner: Spinner
        :type  spinner: okaara.progress.Spinner
        """
        if task.progress_report is not None:
            self.renderer.display_report(task.progress_report)

    def run(self, **kwargs):
        """
        Refresh content sources.
        """
        self.context.prompt.render_title(self.TITLE)
        content_source_id = kwargs[options.OPTION_CONTENT_SOURCE_ID.keyword]
        if content_source_id:
            response = self.context.server.content_source.refresh(content_source_id)
        else:
            response = self.context.server.content_source.refresh_all()
        refresh_task = response.response_body
        self.poll([refresh_task], kwargs)
