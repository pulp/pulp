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
Contains functions for rendering the sync/publish progress reports.
"""

from gettext import gettext as _
import time

# -- public -------------------------------------------------------------------

def display_task_status(context, renderer, task_id):
    """
    Displays and continues to poll and update the sync or publish operation
    taking place in the given task.

    :param context: CLI context
    :type  context: pulp.client.extensions.core.ClientContext
    :param renderer: StatusRenderer subclass that will interpret the sync or
           publish progress report
    :type  renderer: StatusRenderer
    :param task_id: task to display
    :type  task_id: str
    """

    # Retrieve the task and wrap into a list for consistent rendering
    response = context.server.tasks.get_task(task_id)
    task_list = response.response_body

    _display_status(context, renderer, task_list)

def display_group_status(context, renderer, task_group_id):
    """
    Displays and continues to poll and update the sync or publish operation
    taking place in the given task group. This call is used for tracking
    sync operations with one or more distributors configured for auto
    publish.

    :param context: CLI context
    :type  context: pulp.client.extensions.core.ClientContext
    :param renderer: StatusRenderer subclass that will interpret the sync or
           publish progress report
    :type  renderer: StatusRenderer
    :param task_group_id: task group to display
    :type  task_group_id: str
    """

    # Get the list of tasks relevant to the group
    response = context.server.task_groups.get_task_group(task_group_id)
    task_list = response.response_body

    _display_status(context, renderer, task_list)

# -- private ------------------------------------------------------------------

def _display_status(context, renderer, task_list):

    m = _('This command may be exited by pressing ctrl+c without affecting the actual operation on the server.')
    context.prompt.render_paragraph(m)

    # Handle the cases where we don't want to honor the foreground request
    if task_list[0].is_rejected():
        announce = _('The request to synchronize repository was rejected')
        description = _('This is likely due to an impending delete request for the repository.')

        context.prompt.render_failure_message(announce)
        context.prompt.render_paragraph(description)
        return

    if task_list[0].is_postponed():
        a  = _('The request to synchronize the repository was accepted but postponed '
               'due to one or more previous requests against the repository. The sync will '
               'take place at the earliest possible time.')
        context.prompt.render_paragraph(a, tag='postponed')
        return

    completed_tasks = []
    try:
        for task_num, task in enumerate(task_list):
            quiet_waiting = task_num > 0

            task = _display_task_status(context, renderer, task.task_id, quiet_waiting=quiet_waiting)
            completed_tasks.append(task)

    except KeyboardInterrupt:
        # If the user presses ctrl+c, don't let the error bubble up, just
        # exit gracefully
        return

def _display_task_status(context, renderer, task_id, quiet_waiting=False):
    """
    Poll an individual task and display the progress for it.
    @return: the completed task
    @rtype: Task
    """

    begin_spinner = context.prompt.create_spinner()
    poll_frequency_in_seconds = float(context.config['output']['poll_frequency_in_seconds'])

    response = context.server.tasks.get_task(task_id)

    while not response.response_body.is_completed():

        if response.response_body.is_waiting() and not quiet_waiting:
            begin_spinner.next(_('Waiting to begin'))
        else:
            renderer.display_report(response.response_body.progress)

        time.sleep(poll_frequency_in_seconds)

        response = context.server.tasks.get_task(response.response_body.task_id)

    # Even after completion, we still want to display the report one last
    # time in case there was no poll between, say, the middle of the
    # package download and when the task itself reports as finished. We
    # don't want to leave the UI in that half-finished state so this final
    # call is to clean up and render the completed report.
    renderer.display_report(response.response_body.progress)

    return response.response_body

