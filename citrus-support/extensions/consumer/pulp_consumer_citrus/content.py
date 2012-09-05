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

"""
Contains package (RPM) management section and commands.
"""

import time
from gettext import gettext as _
from command import PollingCommand
from pulp.client.extensions.extensions import PulpCliSection
from pulp.bindings.exceptions import NotFoundException
from pulp.client.consumer_utils import load_consumer_id

TYPE_ID = 'repository'

class ContentSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(
            self,
            'content',
            _('content management on downstream pulp servers'))
        for Command in (Update,):
            command = Command(context)
            command.create_option(
                '--pulp-id',
                _('identifies the pulp server'),
                required=True)
            self.add_command(command)


class Update(PollingCommand):

    def __init__(self, context):
        PollingCommand.__init__(
            self,
            'update',
            _('update content on a downstream pulp server'),
            self.run,
            context)
        self.create_option(
            '--repo-id',
            _('unique identifier of a repository'),
            required=False,
            allow_multiple=True,
            aliases=['-r'])
        self.create_flag(
            '--all',
            _('update all bound repositories'),
            aliases=['-a'])

    def run(self, **kwargs):
        all = kwargs['all']
        repo_ids = kwargs['repo-id']
        pulp_id = load_consumer_id(self.context)
        units = []
        options = dict(all=all)
        if all: # ALL
            unit = dict(type_id=TYPE_ID, unit_key=None)
            self.update(pulp_id, [unit], options)
            return
        if repo_ids is None:
            repo_ids = []
        for repo_id in repo_ids:
            unit_key = dict(repo_id=repo_id)
            unit = dict(type_id=TYPE_ID, unit_key=unit_key)
            units.append(unit)
        self.update(pulp_id, units, options)

    def update(self, pulp_id, units, options):
        prompt = self.context.prompt
        server = self.context.server
        if not units:
            msg = 'No repositories specified'
            prompt.render_failure_message(_(msg))
            return
        try:
            response = server.consumer_content.update(pulp_id, units=units, options=options)
            task = response.response_body
            msg = _('Update task created with id [%s]') % task.task_id
            prompt.render_success_message(msg)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
            if self.rejected(task):
                return
            if self.postponed(task):
                return
            self.process(pulp_id, task)
        except NotFoundException:
            msg = _('Consumer [%s] not found') % pulp_id
            prompt.write(msg, tag='not-found')

    def succeeded(self, id, task):
        prompt = self.context.prompt
        # reported as failed
        if not task.result['status']:
            msg = 'Update failed'
            details = task.result['details'][TYPE_ID]['details']
            prompt.render_failure_message(_(msg))
            prompt.render_failure_message(details['message'])
            return
        msg = 'Update Succeeded'
        prompt.render_success_message(_(msg))
        # reported as succeeded
        details = task.result['details'][TYPE_ID]['details']
        prompt.render_success_message(_('succeeded'))
        from pprint import pprint
        pprint(details)