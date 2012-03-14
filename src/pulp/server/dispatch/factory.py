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

from pulp.server import config as pulp_config
from pulp.server.dispatch import context, pickling
from pulp.server.dispatch.coordinator import Coordinator
from pulp.server.dispatch.scheduler import Scheduler
from pulp.server.dispatch.taskqueue import TaskQueue

# globals ----------------------------------------------------------------------

_COORDINATOR = None
_SCHEDULER = None
_TASK_QUEUE = None

# initialization ---------------------------------------------------------------

def _initialize_coordinator():
    global _COORDINATOR
    assert _COORDINATOR is None
    assert isinstance(_TASK_QUEUE, TaskQueue)
    task_state_poll_interval = pulp_config.config.getfloat('coordinator', 'task_state_poll_interval')
    _COORDINATOR = Coordinator(_TASK_QUEUE, task_state_poll_interval)
    _COORDINATOR.start()


def _initialize_scheduler():
    global _SCHEDULER
    assert _SCHEDULER is None
    assert isinstance(_COORDINATOR, Coordinator)
    dispatch_interval = pulp_config.config.getfloat('scheduler', 'dispatch_interval')
    _SCHEDULER = Scheduler(_COORDINATOR, dispatch_interval)
    _SCHEDULER.start()


def _initialize_task_queue():
    global _TASK_QUEUE
    assert _TASK_QUEUE is None
    concurrency_threshold = pulp_config.config.getint('task_queue', 'concurrency_threshold')
    dispatch_interval = pulp_config.config.getfloat('task_queue', 'dispatch_interval')
    _TASK_QUEUE = TaskQueue(concurrency_threshold, dispatch_interval)
    _TASK_QUEUE.start()


def initialize():
    # order sensitive
    context.initialize()
    pickling.initialize()
    _initialize_task_queue()
    _initialize_coordinator()
    _initialize_scheduler()

# factory functions ------------------------------------------------------------

def context():
    """
    Dispatch context factory. Returns thread-local storage holding pertinent
    information and operations for the dispatch environment.
    @return: thread-local storage
    @rtype:  context.Context
    """
    return context.context()


def coordinator():
    """
    Dispatch coordinator factory. Returns the current coordinator instance.
    @return: coordinator for conflicting operation detection and asynchronous execution of calls
    @rtype:  Coordinator
    """
    assert isinstance(_COORDINATOR, Coordinator)
    return _COORDINATOR


def scheduler():
    """
    Dispatch scheduler factory. Returns the current scheduler instance.
    @return: scheduler for delayed and/or repeating calls at regular intervals
    @rtype:  Scheduler
    """
    assert isinstance(_SCHEDULER, Scheduler)
    return _SCHEDULER
