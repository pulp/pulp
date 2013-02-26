# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import httplib

from time import sleep
from gettext import gettext as _

from pulp.server.dispatch.constants import CALL_COMPLETE_STATES, CALL_ERROR_STATE


# --- i18m ------------------------------------------------------------------------------


FETCH_TASK_FAILED = _('Fetch task %(t)s, failed: http=%(c)s')
TASK_FAILED = _('Task %(t)s, failed: state=%(s)s')


# --- exceptions ------------------------------------------------------------------------


class TaskFailed(Exception):
    pass


# --- polling ---------------------------------------------------------------------------

class TaskPoller(object):
    """
    The task poller is used to poll a running task by ID.
    :ivar binding: A pulp API binding.
    :type binding: pulp_node.handlers.model.PulpBinding
    :ivar delay: The delay in seconds between each poll.
    :type delay: int
    :ivar poll: The main loop latch.
    :type poll: bool
    """

    DELAY = 1

    def __init__(self, binding, delay=DELAY):
        """
        :ivar binding: A pulp API binding.
        :type binding: pulp_node.handlers.model.PulpBinding
        :ivar delay: The delay in seconds between each poll.
        :type delay: int
        """
        self.binding = binding
        self.delay = delay
        self.poll = True

    def abort(self):
        """
        Abort polling.
        """
        self.poll = False

    def join(self, task_id, progress):
        """
        Begin polling the specified task.
        This call blocks until the task has completed.
        :param task_id: A task ID.
        :type task_id: str
        :param progress: A progress reporting object.
        :type progress: pulp_node.progress.RepositoryProgress
        :return: The task result.
        """
        last_hash = 0

        while self.poll:
            sleep(self.delay)

            http = self.binding.tasks.get_task(task_id)
            if http.response_code != httplib.OK:
                msg = FETCH_TASK_FAILED % {'t': task_id, 'c': http.response_code}
                raise Exception(msg)

            task = http.response_body
            last_hash = self._report_progress(progress, task, last_hash)

            if task.state == CALL_ERROR_STATE:
                msg = TASK_FAILED % {'t': task_id, 's': task.state}
                raise TaskFailed(msg, task.exception, task.traceback)

            if task.state in CALL_COMPLETE_STATES:
                return task.result

    def _report_progress(self, progress, task, last_hash):
        """
        Update the progress report only if the progress in the task has changed.
        :param progress: A progress reporting object.
        :type progress: pulp_node.progress.RepositoryProgress
        :param task: A task
        :type task: Task
        :param last_hash: The hash of the last reported progress.
        :type last_hash: int
        :return The new hash.
        :rtype: int
        """
        _hash = hash(repr(task.progress))
        if _hash != last_hash:
            if task.progress:
                reported = task.progress.values()[0]
                progress.__dict__.update(reported)
                progress.updated()
        return _hash