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

from pulp.citrus.progress import ProgressReport
from pulp.server.dispatch.constants import CALL_COMPLETE_STATES, CALL_ERROR_STATE


class TaskFailed(Exception):
    pass


class TaskPoller:

    DELAY = 0.5

    def __init__(self, binding):
        self.binding = binding
        self.poll = True

    def abort(self):
        self.poll = False

    def join(self, task_id, progress):
        last_hash = 0
        while self.poll:
            sleep(self.DELAY)
            http = self.binding.tasks.get_task(task_id)
            if http.response_code != httplib.OK:
                msg = 'Fetch task %s, failed: http=%s' % task_id, http.response_code
                raise Exception(msg)
            task = http.response_body
            last_hash = self.report_progress(progress, task, last_hash)
            if task.state == CALL_ERROR_STATE:
                msg = 'Task %s, failed: state=%s' % (task_id, task.state)
                raise TaskFailed(msg, task.exception, task.traceback)
            if task.state in CALL_COMPLETE_STATES:
                return task.result

    def report_progress(self, progress, task, last_hash):
        _hash = hash(repr(task.progress))
        if _hash != last_hash:
            if task.progress:
                reported = task.progress.values()[0]
                report = ProgressReport()
                report.steps = reported['steps']
                report.action = reported['action']
                progress.set_nested_report(report)
        return _hash