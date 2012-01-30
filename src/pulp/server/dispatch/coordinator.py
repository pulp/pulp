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

import datetime
import time

from pulp.server.db.model.dispatch import CoordinatorTask
from pulp.server.dispatch import call, task, taskqueue
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import exceptions as dispatch_exceptions

# coordinator class ------------------------------------------------------------

class Coordinator(object):

    def __init__(self, task_queue, task_wait_sleep_interval=0.5):
        assert isinstance(task_queue, taskqueue.TaskQueue)
        self.task_queue = task_queue
        self.task_collection = CoordinatorTask.get_collection()
        self.task_wait_sleep_interval = task_wait_sleep_interval

    # execution methods --------------------------------------------------------

    def run_task(self, call_request):
        pass

    def run_task_sync(self, call_request, timeout=None):
        pass

    def run_task_async(self, call_request):
        pass

    def run_job(self, call_request_list):
        pass

    def _wait_for_task(self, task, states=dispatch_constants.CALL_COMPLETE_STATES, timeout=None):
        start = datetime.datetime.now()
        while task.call_report.state not in states:
            time.sleep(self.task_wait_sleep_interval)
            if timeout is None:
                continue
            now = datetime.datetime.now()
            if now - start < timeout:
                continue
            # TODO raise timeout error

    def _find_blocking_tasks(self, resources):
        pass

    def _is_rejected(self, resources):
        pass

    # query methods ------------------------------------------------------------

    def find_call_reports(self, **criteria):
        pass

    # control methods ----------------------------------------------------------

    def cancel_task(self, task_id):
        pass

    def cancel_job(self, job_id):
        pass

