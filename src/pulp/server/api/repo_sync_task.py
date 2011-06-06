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
        super(RepoSyncTask, self).__init__(callable, args, kwargs, timeout)
        self.repo_api = None
        self.repo_id = None
        self.synchronizer = None

    def set_synchronizer(self, repo_api, repo_id, sync_obj):
        """
        @param repo_api: instance of a repository api
        @type repo_api: pulp.server.api.repo.RepoApi
        @param repo_id: repository id
        @type repo_id: str
        @param sync_obj
        @type sync_obj: instance of pulp.sever.api.repo_sync.BaseSynchronizer
        """
        # To avoid a circular reference we require an instance of repo_api to be passed in
        self.repo_api = repo_api
        self.repo_id = repo_id
        self.synchronizer = sync_obj
        self.kwargs['synchronizer'] = self.synchronizer

    def cancel(self):
        log.info("RepoSyncTask cancel invoked")
        # Tell Grinder to stop syncing
        if self.synchronizer:
            self.synchronizer.stop()
        # Related to bz700508 - fast sync/cancel_sync locks up task subsystem
        # Removed injecting a CancelException into thread
        # Allow thread to stop on it's own when it reaches a safe stopping point

    def snapshot(self):
        # self grooming
        repo_api = self.repo_api
        synchronizer = self.synchronizer
        self.repo_api = self.synchronizer = None
        self.kwargs.pop('synchronizer', None)
        # create the snapshot
        snapshot = super(RepoSyncTask, self).snapshot()
        snapshot['synchronizer_class'] = pickle.dumps(None)
        if None not in (repo_api, synchronizer):
            snapshot['synchronizer_class'] = pickle.dumps(synchronizer.__class__)
            # restore the grooming
            self.set_synchronizer(repo_api, self.repo_id, synchronizer)
        return snapshot

    @classmethod
    def from_snapshot(cls, snapshot):
        # create task using base class
        task = super(RepoSyncTask, cls).from_snapshot(snapshot)
        # restore synchronizer, if applicable
        synchronizer_class = pickle.loads(snapshot['synchronizer_class'])
        if synchronizer_class is not None:
            from pulp.server.api.repo import RepoApi # avoid circular import
            task.set_synchronizer(RepoApi(), task.repo_id, synchronizer_class())
        return task
