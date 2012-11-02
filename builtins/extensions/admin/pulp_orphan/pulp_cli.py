# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
