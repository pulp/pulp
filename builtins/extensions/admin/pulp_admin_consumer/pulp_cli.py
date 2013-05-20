# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

from pulp.client.commands.consumer.manage import ConsumerUnregisterCommand, ConsumerUpdateCommand
from pulp.client.commands.consumer.query import ConsumerListCommand, ConsumerSearchCommand, ConsumerHistoryCommand

# -- framework hook -----------------------------------------------------------

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
