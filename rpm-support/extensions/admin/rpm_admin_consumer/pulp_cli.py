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

from consumer_group_bind import (ConsumerGroupBindCommand,
                                 ConsumerGroupUnbindCommand)
from consumer_group_package import ConsumerGroupPackageSection
from bind import BindCommand, UnbindCommand
from errata import ErrataSection
from group import GroupSection
from package import PackageSection

# -- framework hook -----------------------------------------------------------

def initialize(context):
    parent_section = context.cli.find_section('consumer')

    # New subsections
    parent_section.add_subsection(PackageSection(context))
    parent_section.add_subsection(GroupSection(context))
    parent_section.add_subsection(ErrataSection(context))

    # Replace the bind/unbind
    parent_section.remove_command('bind')
    m = 'binds a consumer to a repository'
    parent_section.add_command(BindCommand(context, 'bind', _(m)))

    parent_section.remove_command('unbind')
    m = 'removes the binding between a consumer and a repository'
    parent_section.add_command(UnbindCommand(context, 'unbind', _(m)))

    parent_section.remove_subsection('content')

    # Replace the bind/unbind command for consumer groups
    consumer_group_section = parent_section.find_subsection('group')

    consumer_group_section.remove_command('bind')
    m = _('binds each consumer in a consumer group to a repository')
    consumer_group_section.add_command(
        ConsumerGroupBindCommand(context, 'bind', m))

    consumer_group_section.remove_command('unbind')
    m = _('unbinds each consumer in a consumer group from a repository')
    consumer_group_section.add_command(
        ConsumerGroupUnbindCommand(context, 'unbind', m))

    # New subsections for group subsection
    consumer_group_section.add_subsection(ConsumerGroupPackageSection(context))
