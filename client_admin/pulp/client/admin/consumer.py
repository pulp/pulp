from gettext import gettext as _

from pulp.client.commands.consumer.manage import ConsumerUnregisterCommand, ConsumerUpdateCommand
from pulp.client.commands.consumer.query import (ConsumerListCommand, ConsumerSearchCommand,
                                                 ConsumerHistoryCommand)


SECTION_ROOT = 'consumer'
DESC_ROOT = _('display and manage Pulp consumers')


def initialize(context):
    if context.cli.find_section(SECTION_ROOT) is not None:
        return

    consumer_section = context.cli.create_section(SECTION_ROOT, DESC_ROOT)
    consumer_section.add_command(ConsumerListCommand(context))
    consumer_section.add_command(ConsumerSearchCommand(context))
    consumer_section.add_command(ConsumerHistoryCommand(context))
    consumer_section.add_command(ConsumerUnregisterCommand(context))
    consumer_section.add_command(ConsumerUpdateCommand(context))
