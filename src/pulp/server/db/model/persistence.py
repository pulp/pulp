# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

from pulp.server.db.model.base import Model

# task snapshot model ---------------------------------------------------------

class TaskSnapshot(Model):
    """
    Task Snapshot Model
    Store a serialized L{Task} in persistent storage.
    """

    collection_name = "task_snapshots"

    def __init__(self, serialized_task):
        """
        @type task: L{Task} instance
        @param task: task to serialize into a snapshot
        """
        super(TaskSnapshot, self).__init__()
        for key, value in serialized_task.items():
            setattr(self, key, value)
