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

from pulp.server.db.model.dispatch import CoordinatorTask
from pulp.server.dispatch import call, task, taskqueue
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import exceptions as dispatch_exceptions

# coordinator class ------------------------------------------------------------

class Coordinator(object):

    def __init__(self, task_queue):
        assert isinstance(task_queue, taskqueue.TaskQueue)
        self.task_queue = task_queue
        self.task_collection = CoordinatorTask.get_collection()

# conflicting operation detection ----------------------------------------------

OPERATION_MATRIX = (())