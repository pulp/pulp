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

log = logging.getLogger(__name__)

# repo sync task --------------------------------------------------------------

class RepoSyncTask(Task):
    # Note: We want the "invoked" from Task, so we are not inheriting from
    # AsyncTask
    """
    Repository Synchronization Task
    This task is responsible for implementing cancel logic for a
    repository synchronization
    """
    def __init__(self, callable, args=[], kwargs={}, timeout=None):
        super(RepoSyncTask, self).__init__(callable, args, kwargs, timeout=timeout)
        self.repo_id = None

        if len(self.args) > 0:
            # Assuming that args first parameter is always the repo_id
            self.repo_id = self.args[0]
        self.synchronizer = None

    def set_synchronizer(self, sync_obj):
        """
        @param sync_obj
        @type sync_obj: instance of pulp.sever.api.repo_sync.BaseSynchronizer
        """
        self.synchronizer = sync_obj
        self.kwargs['synchronizer'] = self.synchronizer

    def cancel(self):
        log.info("RepoSyncTask cancel invoked repo <%s>. Will cancel synchronizer <%s>" % (self.repo_id, self.synchronizer))
        # Tell Grinder to stop syncing
        if self.synchronizer:
            self.synchronizer.stop()
        log.info("RepoSyncTask repo <%s> has been canceled" % (self.repo_id))
        # Related to bz700508 - fast sync/cancel_sync locks up task subsystem
        # Removed injecting a CancelException into thread
        # Allow thread to stop on it's own when it reaches a safe stopping point

    def snapshot(self):
        # self grooming
        self.kwargs.pop('synchronizer', None)
        # create the snapshot
        snapshot = super(RepoSyncTask, self).snapshot()
        snapshot['repo_id'] = self.repo_id
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
        task = super(RepoSyncTask, cls).from_snapshot(snapshot)
        task.repo_id = snapshot['repo_id']
        # restore synchronizer, if applicable
        synchronizer_class = pickle.loads(snapshot['synchronizer_class'])
        if synchronizer_class is None:
            # Most likely this task has been snapshotted before we set a synchronizer object
            # it's our responsibility to ensure the synchronizer object is set, failure to do this
            # will break ability to cancel a sync.
            from pulp.server.api.repo import RepoApi # avoid circular import
            r = RepoApi().repository(task.repo_id, fields=["content_types"])
            if r and r.has_key("content_types") and r["content_types"] is not None:
                repo_content_type = r["content_types"]
                from pulp.server.api.repo_sync import get_synchronizer # avoid circular import
                synchronizer_class = get_synchronizer(repo_content_type).__class__
        if synchronizer_class is not None:
            task.set_synchronizer(synchronizer_class())
        return task
