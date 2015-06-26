from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliCommand


def initialize(context):
    """
    Add status to the root of the CLI, not in a specific section.

    :param context: The client context.
    :type context: pulp.client.extensions.core.ClientContextt
    """
    context.cli.add_command(StatusCommand(context))


class StatusCommand(PulpCliCommand):
    """
    Shows server's status and details.
    """
    NAME = 'status'
    DESCRIPTION = _('shows server\'s status')
    TITLE = _('Status of the server')

    def __init__(self, context):
        """
        :param context: The client context.
        :type context: pulp.client.extensions.core.ClientContext
        """
        PulpCliCommand.__init__(self, self.NAME, self.DESCRIPTION, self.status)

        self.context = context
        self.api = context.server.server_status

    def status(self):
        """
        Queries server's status.
        """
        self.context.prompt.render_title(self.TITLE)
        server_status = self.api.get_status()
        self.context.prompt.render_document(server_status.response_body, omit_hidden=False)
