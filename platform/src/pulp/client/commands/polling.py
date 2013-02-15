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

import time
from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliCommand


class PollingCommand(PulpCliCommand):
    """
    A polling command provides support for polling tasks created during
    REST calls to the server.  Primarily, it polls the server for an updated
    status for the task.  Once the task is finished, it is dispatched to
    a method based on task status.  Additionally, it stores the context
    for convenience.

    :ivar context: The command context object.
    :type context: See okaara.
    """

    def __init__(self, name, description, method, context):
        """
        :param name: The command name.
        :type name: str
        :param description: The command description.
        :type description: str
        :param method: The command (main) method.
        :type method: instancemethod
        :param context: The command context object.
        :type context: See okaara.
        """
        super(PollingCommand, self).__init__(name, description, method)
        self.context = context

    def process(self, resource_id, task):
        """
        Process the queued task by polling and waiting for it to complete.
        Once the task has completed, it is dispatched to a method based
        on the task status.  A spinner is displayed while polling.

        :param resource_id: The resource ID.
        :type resource_id: str
        :param task: A queued task.
        :type task: Task
        """
        msg = _('This command may be exited via ctrl+c without affecting the request.')
        self.context.prompt.render_paragraph(msg)

        try:
            task = self._poll(task)

            if task.was_successful():
                return self.succeeded(resource_id, task)

            if task.was_failure():
                return self.failed(resource_id, task)

            if task.was_cancelled():
                return self.cancelled(resource_id, task)

        # graceful interrupt
        except KeyboardInterrupt:
            pass

    def _poll(self, task):
        """
        Poll the server, waiting for a task completion.

        :param task: A queued task.
        :type task: Task
        :return: The completed task.
        :rtype: Task
        """
        spinner = self.context.prompt.create_spinner()
        interval = float(self.context.config['output']['poll_frequency_in_seconds'])
        last_hash = None

        while not task.is_completed():
            if task.is_waiting():
                spinner.next(_('Waiting to begin'))

            else:
                # report progress only if valid & changed
                if task.progress:
                    _hash = hash(repr(task.progress))

                    if _hash != last_hash:
                        self.progress(task.progress)
                        last_hash = _hash

                else:
                    spinner.next()

            time.sleep(interval)

            response = self.context.server.tasks.get_task(task.task_id)
            task = response.response_body

        if task.progress:
            self.progress(task.progress)

        return task

    def progress(self, report):
        """
        The task has reported progress

        :param report: A progress report.
        """
        self.context.prompt.render_document(report)

    def rejected(self, task):
        """
        Test for rejected tasks.
        If rejected, an appropriate message is displayed for the user and
        and the test result (flag) is returned.

        :param task: A queued task.
        :type task: Task
        :return: Whether the task was rejected.
        :rtype: bool
        """
        rejected = task.is_rejected()

        if rejected:
            msg = _('The request was rejected by the server.\n'
                    'This is likely due to an impending delete request for the resource.')
            self.context.prompt.render_failure_message(_(msg))

        return rejected

    def postponed(self, task):
        """
        Test for postponed tasks.
        If postponed, an appropriate message is displayed for the user and
        and the test result (flag) is returned.
        :param task: A queued task.
        :type task: Task
        :return: Whether the task was postponed.
        :rtype: bool
        """
        postponed = task.is_postponed()

        if postponed:
            msg  = _('The request was accepted but postponed due to one or more previous requests against the resource.\n'
                     'This request will proceed at the earliest possible time.')
            self.context.prompt.render_paragraph(msg)

        return postponed

    def succeeded(self, resource_id, task):
        """
        Called when a task has completed with a status indicating success.
        Must be overridden by subclasses which are expected to print the
        appropriate output to the user.

        :param resource_id: The resource ID.
        :type resource_id: str
        :param task: A successful task.
        :type task: Task
        """
        msg = _('Request Succeeded')
        self.context.prompt.render_success_message(msg)

    def failed(self, resource_id, task):
        """
        Called when a task has completed with a status indicating that it failed.
        An appropriate message is displayed to the user.

        :param resource_id: The resource ID.
        :type id: str
        :param task: A cancelled task.
        :type task: Task
        """
        msg = _('Request Failed')
        self.context.prompt.render_failure_message(msg)
        self.context.prompt.render_failure_message(task.exception)

    def cancelled(self, resource_id, task):
        """
        Called when a task has completed with a status indicating
        that it was cancelled.
        An appropriate message is displayed to the user.

        :param resource_id: The resource ID.
        :type resource_id: str
        :param task: A cancelled task.
        :type task: Task
        """
        msg = _('Request Cancelled')
        self.context.prompt.write(msg)

