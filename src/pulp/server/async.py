# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

from pulp.server.tasking.queue.fifo import FIFOTaskQueue
from pulp.server.tasking.task import Task

# async execution queue -------------------------------------------------------

queue = FIFOTaskQueue()

# async api -------------------------------------------------------------------

def run_async(method, args, kwargs, timeout=None, unique=True):
    """
    """
    task = Task(method, args, kwargs, timeout)
    if queue.enqueue(task, unique):
        return task
    return None

cancel_async = queue.cancel

find_async = queue.find
