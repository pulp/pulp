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
Base class for RPM admin commands.
"""

import time
from gettext import gettext as _
from pulp.client.extensions.extensions import PulpCliCommand

class PollingCommand(PulpCliCommand):

    def __init__(self, name, description, method, context):
        PulpCliCommand.__init__(self, name, description, method)
        self.context = context

    def process(self, id, task):
        prompt = self.context.prompt
        m = 'This command may be exited via ctrl+c without affecting the install.'
        prompt.render_paragraph(_(m))
        try:
            task = self.poll(task)
            if task.was_successful():
                self.succeeded(id, task)
                return
            if task.was_failure():
                self.failed(id, task)
                return
            if task.was_cancelled():
                self.cancelled(id, task)
                return
        except KeyboardInterrupt:
            # graceful interrupt
            pass

    def poll(self, task):
        server = self.context.server
        cfg = self.context.config
        spinner = self.context.prompt.create_spinner()
        interval = float(cfg['output']['poll_frequency_in_seconds'])
        while not task.is_completed():
            if task.is_waiting():
                spinner.next(_('Waiting to begin'))
            else:
                spinner.next()
            time.sleep(interval)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
        return task

    def rejected(self, task):
        rejected = task.is_rejected()
        if rejected:
            prompt = self.context.prompt
            msg = 'The request was rejected by the server'
            prompt.render_failure_message(_(msg))
            msg = 'This is likely due to an impending delete request for the consumer.'
            prompt.render_failure_message(_(msg))
        return rejected

    def postponed(self, task):
        postponed = task.is_postponed()
        if postponed:
            msg  = \
                'The request to update content was accepted but postponed ' \
                'due to one or more previous requests against the consumer.' \
                ' This request will take place at the earliest possible time.'
            self.context.prompt.render_paragraph(_(msg))
        return postponed

    def succeeded(self, id, task):
        raise NotImplementedError()

    def failed(self, id, task):
        prompt = self.context.prompt
        msg = 'Request Failed'
        prompt.render_failure_message(_(msg))
        prompt.render_failure_message(task.exception)

    def cancelled(self, id, response):
        prompt = self.context.prompt
        prompt.render_failure_message('Request Cancelled')