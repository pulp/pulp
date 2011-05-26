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

import pickle

from pulp.server.db.model.base import Model

# task snapshot model ---------------------------------------------------------

class TaskSnapshot(Model):
    """
    Task Snapshot Model
    Store a serialized L{Task} in persistent storage.
    """

    collection_name = "task_snapshots"
    unique_indicies = ()
    other_indicies = ('id', 'state')

    def __init__(self, serialized_task=None):
        """
        @type task: L{Task} instance
        @param task: task to serialize into a snapshot
        """
        # XXX allow detect SON serialized task and properly handle the
        # necessary string conversions
        serialized_task = serialized_task or {}
        super(TaskSnapshot, self).__init__()
        self.update(self._process_serialized_task(serialized_task))

    def _process_serialized_task(self, serialized_task):
        # we're using ascii pickling, but the mongodb converts all string to
        # unicode, so we need to convert them back in order to properly load
        # snapshots from the database
        def _process_value(value):
            if not isinstance(value, basestring):
                return value
            return unicode(value).encode('ascii').strip()

        return dict([(k, _process_value(v)) for k, v in serialized_task.items()])

    def to_task(self):
        """
        De-serialize this snapshot into a task using the serialized task class.
        @rtype: L{pulp.server.tasking.task.Task} instance
        @return: de-serialized task represented by this snapshot
        """
        task_class = self.get('task_class', None)
        if task_class is None:
            raise Exception()
        cls = pickle.loads(task_class)
        return cls.from_snapshot(self)
