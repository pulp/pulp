# Copyright (c) 2012 Red Hat, Inc.
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

from pulp.server.dispatch.constants import CALL_COMPLETE_STATES, CALL_ERROR_STATE


class TaskPoller:

    PROGRESS_DELAY = 0.5

    def __init__(self, binding, progress):
        self.binding = binding
        self.progress = progress

    def join(self, task_id):
        last_hash = 0
        while True:
            sleep(self.PROGRESS_DELAY)
            http = self.binding.tasks.get_task(task_id)
            if http.response_code != httplib.OK:
                break
            task = http.response_body
            last_hash = self.report_progress(task, last_hash)
            if task.state == CALL_ERROR_STATE:
                break
            if task.state in CALL_COMPLETE_STATES:
                return

    def report_progress(self, task, last_hash):
        _hash = hash(repr(task.progress))
        if _hash != last_hash:
            self.progress.set_action('task', task.progress)
        return _hash