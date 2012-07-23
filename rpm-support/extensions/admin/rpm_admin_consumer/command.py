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
    """
    A I{polling} command provides support for polling tasks created during
    REST calls to the server.  Primarily, it polls the server for an updated
    status for the task.  Once the task is finished, it is dispatched to
    a method based on task status.  Additionally, it stores the I{context}
    for convenience.
    @ivar context: The command context object.
    @type context: See okaara.
    """

    def __init__(self, name, description, method, context):
        """
        @param name: The command name.
        @type name: str
        @param description: The command description.
        @type description: str
        @param method: The command (main) method.
        @type method: instancemethod
        @param context: The command context object.
        @type context: See okaara.
        """
        PulpCliCommand.__init__(self, name, description, method)
        self.context = context

    def process(self, id, task):
        """
        Process the queued task by polling and waiting for it to complete.
        Once the task has completed, it is dispatched to a method based
        on the task status.  A spinner is displayed while polling.
        @type id: The consumer ID.
        @type id: str
        @param task: A queued task.
        @type task: Task
        """
        prompt = self.context.prompt
        m = 'This command may be exited via ctrl+c without affecting the install.'
        prompt.render_paragraph(_(m))
        try:
            task = self._poll(task)
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

    def _poll(self, task):
        """
        Poll the server, waiting for a task completion.
        @param task: A queued task.
        @type task: Task
        @return: The completed task.
        @rtype: Task
        """
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
        """
        Test for rejected tasks.
        If rejected, an appropriate message is displayed for the user and
        and the test result (flag) is returned.
        @param task: A queued task.
        @type task: Task
        @return: Whether the task was rejected.
        @rtype: bool
        """
        rejected = task.is_rejected()
        if rejected:
            prompt = self.context.prompt
            msg = 'The request was rejected by the server'
            prompt.render_failure_message(_(msg))
            msg = 'This is likely due to an impending delete request for the consumer.'
            prompt.render_failure_message(_(msg))
        return rejected

    def postponed(self, task):
        """
        Test for postponed tasks.
        If postponed, an appropriate message is displayed for the user and
        and the test result (flag) is returned.
        @param task: A queued task.
        @type task: Task
        @return: Whether the task was postponed.
        @rtype: bool
        """
        postponed = task.is_postponed()
        if postponed:
            msg  = \
                'The request to update content was accepted but postponed ' \
                'due to one or more previous requests against the consumer.' \
                ' This request will take place at the earliest possible time.'
            self.context.prompt.render_paragraph(_(msg))
        return postponed

    def succeeded(self, id, task):
        """
        Called when a task has completed with a status indicating success.
        Must be overridden by subclasses which are expected to print the
        appropriate output to the user.
        @type id: The consumer ID.
        @type id: str
        @param task: A successful task.
        @type task: Task
        """
        raise NotImplementedError()

    def failed(self, id, task):
        """
        Called when a task has completed with a status indicating that it failed.
        An appropriate message is displayed to the user.
        @type id: The consumer ID.
        @type id: str
        @param task: A cancelled task.
        @type task: Task
        """
        prompt = self.context.prompt
        msg = 'Request Failed'
        prompt.render_failure_message(_(msg))
        prompt.render_failure_message(task.exception)

    def cancelled(self, id, task):
        """
        Called when a task has completed with a status indicating
        that it was cancelled.
        An appropriate message is displayed to the user.
        @type id: The consumer ID.
        @type id: str
        @param task: A cancelled task.
        @type task: Task 
        """
        prompt = self.context.prompt
        prompt.render_failure_message('Request Cancelled')