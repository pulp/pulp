# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from uuid import uuid4

class Job(object):
    """
    @ivar id: The unique id.
    @type id: str
    @ivar tasks: Contained task objects.
    @type tasks: list
    """

    def __init__(self):
        self.id = str(uuid4())
        self.tasks = []

    def add(self, task):
        """
        Add the specified task.
        @param task: A task to be added to the job.
        @type task: Task
        """
        task.job_id = self.id
        self.tasks.append(task)
