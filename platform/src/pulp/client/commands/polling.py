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
Contains base classes for commands that poll the server for asynchronous tasks.
"""

import time
from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliCommand


# Returned from the poll command if one or more of the tasks in the given list
# was rejected
RESULT_REJECTED = 'rejected'

# Returned from the poll command if the user gracefully aborts the polling
RESULT_ABORTED = 'aborted'


class PollingCommand(PulpCliCommand):
    """
    Base class for commands that wish to track a task executed on the server.
    Subclasses should override the rendering methods as appropriate to display
    custom messages based on the task state or progress.

    If the poll_frequency_in_seconds is not specified, it will be loaded from
    the configuration under output -> poll_frequency_in_seconds.

    :ivar context: the client context
    :type context: pulp.client.extensions.core.ClientContext
    """

    def __init__(self, name, description, method, context, poll_frequency_in_seconds=None):
        """
        :param name: command name
        :type  name: str
        :param description: command description
        :type  description: str
        :param method: method that will be fun when the command is invoked
        :type  method: function
        :param context: client context
        :type  context: pulp.client.extensions.core.ClientContext
        :param poll_frequency_in_seconds: time between polling calls to the server
        :type  poll_frequency_in_seconds: float
        """
        super(PollingCommand, self).__init__(name, description, method)
        self.context = context
        self.prompt = context.prompt

        self.poll_frequency_in_seconds = poll_frequency_in_seconds
        if poll_frequency_in_seconds is None:
            self.poll_frequency_in_seconds = float(self.context.config['output']['poll_frequency_in_seconds'])

    def poll(self, task_list):
        """
        Entry point to begin polling on the tasks in the given list. Each task will be polled
        in order until completion. If an error state is encountered, polling of the remaining
        tests will be stopped.

        This method is intended to handle all task states, from waiting to rejected. The
        appropriate message method below will be called depending on the state encounteres.
        Subclasses should override these methods as necessary to customize the message displayed.

        While each task is being polled, the progress method will be called at regular
        intervals to allow the subclass to display information on the state of the task.

        :param task_list: list of task reports received from the initial call to the server
        :type  task_list: list of pulp.bindings.responses.Task

        :return: the final task reports for all of the tasks
        """

        # I'm not sure the server has the potential to return an empty list of tasks if nothing
        # was queued, but in case it does account for it here so the caller doesn't have to
        # check anything about the task list before calling this.
        if len(task_list) == 0:
            return []

        # If one task is rejected, they will all be marked as rejected, so we can simply
        # check the first in the list.
        if task_list[0].is_rejected():
            self.rejected(task_list[0])
            return RESULT_REJECTED

        msg = _('This command may be exited via ctrl+c without affecting the request.')
        self.prompt.render_paragraph(msg, tag='abort')

        try:
            # Keep a copy of the final reports for all tasks to return to the caller
            completed_task_list = []

            for task in task_list:

                # If there are more than one tasks to poll, we need to display a divider so
                # the user knows which task is being followed.
                if len(task_list) > 1:
                    self.task_header(task)

                task = self._poll_task(task)

                # Display the appropriate message based on the result of the task

                if task.was_successful():
                    self.succeeded(task)

                if task.was_failure():
                    self.failed(task)

                if task.was_cancelled():
                    self.cancelled(task)

                completed_task_list.append(task)

            return completed_task_list

        except KeyboardInterrupt:
            # Gracefully handle if the user aborts the polling.
            return RESULT_ABORTED


    def _poll_task(self, task):
        """
        Handles a specific task in the task list until it has completed. This call will handle
        displaying messages while the task is in the waiting state and making progress callbacks
        into the progress method.

        :param task: A queued task.
        :type  task: pulp.bindings.responses.Task

        :return: the completed task report
        :rtype:  pulp.bindings.responses.Task
        """
        spinner = self.context.prompt.create_spinner()

        while not task.is_completed():

            # Postponed is a more specific version of waiting and must be checked first.
            if task.is_postponed():
                self.postponed(task)
                spinner.next()
            elif task.is_waiting():
                self.waiting(task)
                spinner.next()
            else:
                self.progress(task)

            time.sleep(self.poll_frequency_in_seconds)

            response = self.context.server.tasks.get_task(task.task_id)
            task = response.response_body

        # One final call to update the progress with the end state
        self.progress(task)

        return task

    # -- polling rendering ----------------------------------------------------------------------------------

    def task_header(self, task):
        """
        Displays information to the user to indiciate which task is about to be tracked.
        This is only called once per task immediately before the polling loop begins and
        only if there is more than one task being tracked.

        The default implementation is less user-friendly than many of these render method
        implementations. Typical overridden implementations should check the tags on the task
        and use that to display a user-friendly message about which task is taking place.

        :param task: task about to be polled
        :type  task: pulp.bindings.responses.Task
        """
        template = _('-- Task Tags: %(tags)s ----')
        msg = template % {'tags' : ', '.join(task.tags)}
        self.prompt.render_paragraph(msg, tag='header')

    def waiting(self, task):
        """
        Called while an accepted task (i.e. not postponed) is waiting to begin.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        msg = _('Waiting to begin...')
        self.prompt.write(msg, tag='waiting')

    def postponed(self, task):
        """
        Called when a task is postponed due to the resource being used.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        msg  = _('The request was accepted but postponed due to one or more previous requests '
                 'against the resource. This request will proceed at the earliest possible time.')
        self.prompt.write(msg, tag='postponed')

    # -- task completed rendering ---------------------------------------------------------------------------

    def progress(self, task):
        """
        Called each time a task is polled. The default implementation displays nothing.

        :param task: full task report for the task being displayed
        """
        pass

    def succeeded(self, task):
        """
        Called when a task has completed with a status indicating success.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        msg = _('Request Succeeded')
        self.prompt.render_success_message(msg, tag='succeeded')

    def failed(self, task):
        """
        Called when a task has completed with a status indicating that it failed.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        msg = _('Request Failed')
        self.prompt.render_failure_message(msg, tag='failed')
        self.prompt.render_failure_message(task.exception, tag='failed_exception')

    def cancelled(self, task):
        """
        Called when a task has completed with a status indicating that it was cancelled.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        msg = _('Request Cancelled')
        self.prompt.render_paragraph(msg, tag='cancelled')

    def rejected(self, task):
        """
        Called in the event the task list indicates the request was rejected.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        msg = _('The request was rejected by the server. '
                'This is likely due to an impending delete request for the resource.')
        self.context.prompt.render_failure_message(msg, tag='rejected')
