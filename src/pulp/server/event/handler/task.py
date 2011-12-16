# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""
Contains TASK event handler classes.
"""

import os
from pulp.server.event.dispatcher import *
from pulp.server.event.producer import EventProducer
from pulp.server.config import config
from pulp.server import util
from logging import getLogger

log = getLogger(__name__)


class TaskEvent(EventHandler):
    """
    The I{task} event handler.
    @type rapi: L{RepoApi}
    """

    def __init__(self):
        self.producer = EventProducer()

    @outbound(action='dequeued')
    def finish(self, *args, **kwargs):
        """
        Raise events when a task finishes.
        @param task: The finished task object.
        @type task: Task
        """
        task = args[1]
        event = dict(id=task.id, state=task.state, result=task.result)
        self.producer.send('task.dequeued', event)


class TaskDequeued:
    @event(subject='task.dequeued')
    def __call__(self, task):
        pass


EventDispatcher.register('task', TaskEvent)
