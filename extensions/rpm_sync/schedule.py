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

from pulp.gc_client.framework.extensions import PulpCliSection, PulpCliCommand

class SchedulingSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'schedule', _('repository synchronization scheduling'))
        for Command in (ListScheduled, AddScheduled, DeleteScheduled):
            command = Command(context)
            command.create_option('--repo-id', _('identifies the repository'), required=True)
            self.add_command(command)


class ListScheduled(PulpCliCommand):

    def __init__(self, context):
        PulpCliCommand.__init__(self, 'list', _('list scheduled synchronizations'), self.list)
        self.context = context

    def list(self, **kwargs):
        pass


class AddScheduled(PulpCliCommand):

    def __init__(self, context):
        PulpCliCommand.__init__(self, 'add', _('add a scheduled synchronization'), self.add)
        self.context = context

    def add(self, **kwargs):
        pass


class DeleteScheduled(PulpCliCommand):

    def __init__(self, context):
        PulpCliCommand.__init__(self, 'delete', _('delete a scheduled synchronization'), self.delete)
        self.context = context

    def delete(self, **kwargs):
        pass