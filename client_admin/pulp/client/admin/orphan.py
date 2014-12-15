from gettext import gettext as _

from pulp.client.commands.unit import OrphanUnitListCommand, OrphanUnitRemoveCommand
from pulp.client.extensions.extensions import PulpCliSection


def initialize(context):
    """
    :type  context: pulp.client.extensions.core.ClientContext
    """
    context.cli.add_section(OrphanSection(context))


class OrphanSection(PulpCliSection):
    def __init__(self, context):
        """
        :type  context: pulp.client.extensions.core.ClientContext
        """
        m = _('find and remove orphaned content units')
        super(OrphanSection, self).__init__('orphan', m)

        self.context = context

        self.add_command(OrphanUnitListCommand(context))
        self.add_command(OrphanUnitRemoveCommand(context))
