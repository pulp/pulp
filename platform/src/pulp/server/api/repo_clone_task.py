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

import logging
import pickle

from pulp.server.tasking.task import Task
from pulp.server.api.repo import RepoApi
log = logging.getLogger(__name__)

# repo clone task --------------------------------------------------------------

class RepoCloneTask(Task):
    # Note: We want the "invoked" from Task, so we are not inheriting from
    # AsyncTask
    """
    Repository Cloning Task
    This task is responsible for implementing cancel logic for a
    repository cloning
    """
    def __init__(self, callable, args=[], kwargs={}, timeout=None):
        super(RepoCloneTask, self).__init__(callable, args, kwargs, timeout=timeout)
        self.clone_id = None
        if len(self.args) > 0:
            # Assuming that args first parameter is always the clone_id
            self.clone_id = self.args[0]
        self.synchronizer = None

    def set_synchronizer(self, sync_obj):
        """
        @param sync_obj
        @type sync_obj: instance of pulp.sever.api.repo_sync.BaseSynchronizer
        """
        self.synchronizer = sync_obj
        self.kwargs['synchronizer'] = self.synchronizer

    def cancel(self):
        log.info("RepoCloneTask cancel invoked repo <%s>. Will cancel synchronizer <%s>" % (self.clone_id, self.synchronizer))
        # Tell Grinder to stop syncing
        if self.synchronizer:
            self.synchronizer.stop()
        log.info("RepoCloneTask repo <%s> has been canceled" % (self.clone_id))
        # Related to bz700508 - fast sync/cancel_sync locks up task subsystem
        # Removed injecting a CancelException into thread
        # Allow thread to stop on it's own when it reaches a safe stopping point
        if RepoApi().repository(self.clone_id) is not None:
            RepoApi().delete(self.clone_id)

    def snapshot(self):
        # self grooming
        self.kwargs.pop('synchronizer', None)
        # create the snapshot
        snapshot = super(RepoCloneTask, self).snapshot()
        snapshot['clone_id'] = self.clone_id
        snapshot['synchronizer_class'] = pickle.dumps(None)
        if self.synchronizer is not None:
            #Note: snapshot() is likely called prior to us having set a synchronizer object
            #for most runs this self.synchronizer will be None
            snapshot['synchronizer_class'] = pickle.dumps(self.synchronizer.__class__)
            # restore the grooming
            self.set_synchronizer(self.synchronizer)
        return snapshot

    @classmethod
    def from_snapshot(cls, snapshot):
        # create task using base class
        task = super(RepoCloneTask, cls).from_snapshot(snapshot)
        task.clone_id = snapshot['clone_id']
        # restore synchronizer, if applicable
        synchronizer_class = pickle.loads(snapshot['synchronizer_class'])
        if synchronizer_class is None:
            # Most likely this task has been snapshotted before we set a synchronizer object
            # it's our responsibility to ensure the synchronizer object is set, failure to do this
            # will break ability to cancel a sync.
            r = RepoApi().repository(task.clone_id, fields=["content_types"])
            if r and r.has_key("content_types") and r["content_types"] is not None:
                repo_content_type = r["content_types"]
                from pulp.server.api.repo_sync import get_synchronizer # avoid circular import
                synchronizer_class = get_synchronizer(repo_content_type).__class__
        if synchronizer_class is not None:
            task.set_synchronizer(synchronizer_class())
        return task
