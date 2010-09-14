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

_queue = FIFOTaskQueue()

# async api -------------------------------------------------------------------

find_async = _queue.find

cancel_async = _queue.cancel


def run_async(method, args, kwargs, timeout=None, unique=True):
    """
    Make a python call asynchronously.
    @type method: callable
    @param method: method to call asynchronously
    @type args: list or tuple
    @param args: list of positional arguments for method
    @type kwargs: dict
    @param kwargs: key word arguements for method
    @type timeout: datetime.timedelta instance
    @param timeout: maximum length of time to let method run before interrupting it
    @type unique: bool
    @param unique: whether or not to make sure the task isn't already being run
    @rtype: L{Task} instance or None
    @return: L{Task} instance on success, None otherwise
    """
    task = Task(method, args, kwargs, timeout)
    if _queue.enqueue(task, unique):
        return task
    return None
