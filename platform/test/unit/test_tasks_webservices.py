# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import pprint
import time

import base

from pulp.server.tasking.task import task_complete_states, task_error

# async test functions ---------------------------------------------------------

def ret():
    pass

def wait(seconds=3):
    time.sleep(seconds)

# testting ---------------------------------------------------------------------

class TasksCollectionTest(base.PulpWebserviceTests):

    def _wait_for_task(self, task, timeout=datetime.timedelta(seconds=10)):
        start = datetime.datetime.now()
        while task.state not in task_complete_states:
            time.sleep(0.5)
            if datetime.datetime.now() - start >= timeout:
                raise RuntimeError('Task wait timed out after %d seconds with state: %s' %
                                   (timeout.seconds, task.state))
            if task.state == task_error:
                pprint.pprint(task.traceback)

    def test_get(self):
        status, body = self.get('/tasks/')

