# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
from gettext import gettext as _

from pulp.client.api.task import TaskAPI
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit

# task command -----------------------------------------------------------------

class Task(Command):

    description = _('pulp server asynchronous task administration and debugging')

# task actions -----------------------------------------------------------------

class TaskAction(Action):

    def __init__(self):
        super(TaskAction, self).__init__()
        self.api = TaskAPI()

    def setup_parser(self):
        self.parser.add_option('--id', dest='id', help=_('task id'))


class List(TaskAction):

    description = _('list tasks currently in the tasking system')

    def setup_parser(self):
        self.parser.add_option('--state', dest='state', action='append', default=[],
                               help=_('state of tasks to list. valild states: waiting, running, incomplete, complete, all. defaults to "all"'))


    def run(self):
        tasks = self.api.list(self.opts.state)
        if not tasks:
            system_exit(os.EX_OK, _('No tasks found'))
        # TODO format and list tasks


class Info(TaskAction):

    description = _('show information for a task')

    def run(self):
        id = self.get_required_option('id')
        task = self.api.info(id)
        if not task:
            system_exit(os.EX_OK)
        # TODO format task and print out


class Remove(TaskAction):

    description = _('remove a task from the tasking system')

    def run(self):
        id = self.get_required_option('id')
        task = self.api.remove(id)
        if not task:
            system_exit(os.EX_OK)
        print _('Task [%s] set for removal') % id


class Snapshots(TaskAction):

    description = _('list current task snapshots')

    def setup_parser(self):
        # overridden to supress the --id option
        pass

    def run(self):
        snapshots = self.api.list_snapshots()
        if not snapshots:
            system_exit(os.EX_OK, _('No snapshots found'))
        # TODO format and list snapshots


class Snapshot(TaskAction):

    description = _('show the snapshot for a task')

    def run(self):
        id = self.get_required_option('id')
        snapshot = self.api.info_snapshot(id)
        if not snapshot:
            system_exit(os.EX_OK)
        # TODO format and show snapshot


class DeleteSnapshot(TaskAction):

    description = _('delete a snapshot from the database')

    def run(self):
        id = self.get_required_option('id')
        snapshot = self.api.delete_snapshot('id')
        if not snapshot:
            system_exit(os.EX_OK)
        print _('Snapshot for task [%s] deleted') % id