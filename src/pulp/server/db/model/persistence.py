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

import copy
import pickle
from gettext import gettext as _

from pulp.server.api.repo import RepoSyncTask
from pulp.server.db.model.base import Model
from pulp.server.pexceptions import PulpException
from pulp.server.tasking.task import Task, AsyncTask

# task fields stored in task snapshots ----------------------------------------

_copied_fields = (
    'id',
    'class_name',
    'method_name',
    'timeout',
    'cancel_attempts',
    'state',
    'scheduled_time',
    'start_time',
    'finished_time',
    'exception',
    'traceback',
)

_pickled_fields = (
    'callable',
    'args',
    'kwargs',
    'scheduler',
    'result',
    'synchronizer',
)

# task snapshot model ---------------------------------------------------------

class TaskSnapshot(Model):
    """
    Task Snapshot Model
    Store a L{Task} in a serialized state to enable persistent storage of the
    task information or to restore tasks from the the serialized state.
    """

    _collection_name = "task_snapshots"

    def __init__(self, task):
        """
        @type task: L{Task} instance
        @param task: task to serialize into a snapshot
        """
        super(TaskSnapshot, self).__init__()
        self.task_type = task.__class__.__name__
        for attr in _copied_fields:
            setattr(self, attr, getattr(task, attr, None))
        for attr in _pickled_fields:
            setattr(self, attr, pickle.dumps(getattr(task, attr, None))) # ascii pickle
            #except:
            #   msg = _("Error pickling attribute %s:%s")
            #  raise TaskPicklingError(msg % (attr, getattr(task, attr, None)))

# task restoration api --------------------------------------------------------

class TaskRestorationError(PulpException):
    pass

class TaskPicklingError(PulpException):
    pass

# dir is used here as a placeholder function to get the task back from the serialization 
_task_types = {
    'Task': Task(dir),
    'AsyncTask': AsyncTask(dir),
    'RepoSyncTask': RepoSyncTask(dir),
}


def restore_from_snapshot(snapshot):
    """
    Create a task from a serialized snapshot.
    @type snapshot: dict or BSON instance
    @param snapshot: serialized task snapshot to "restore" from
    @rtype: L{Task} instance
    @return: task equivalent of the snapshot
    """
    task_type = snapshot['task_type']
    try:
        task = copy.deepcopy(_task_types[task_type])
    except KeyError:
        msg = _('Task restoration from snapshot of %s not currently supported')
        raise TaskRestorationError(msg % task_type)

    for attr in _copied_fields:
        setattr(task, attr, snapshot.get(attr, None))
    for attr in _pickled_fields:
        setattr(task, attr, pickle.loads(snapshot.get(attr, 'N.'))) # N. pickled None
    return task
