import logging

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
        self.synchronizer = None
        self.repo_id = None

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
        log.error("__name__ = %s" % (__name__))
        self.repo_api = repo_api
        self.repo_id = repo_id
        self.synchronizer = sync_obj
        self.kwargs['synchronizer'] = self.synchronizer

    def cancel(self):
        log.info("RepoSyncTask cancel invoked")
        # Tell Grinder to stop syncing
        if self.synchronizer:
            self.synchronizer.stop()
            # All synchronization work should be stopped
            # when this returns.  Will pass through to
            # default cancel behavior as a backup in case
            # something didn't cancel
        # Inject the CancelException into the running sync thread
        super(RepoSyncTask, self).cancel()
        # Clean up state of sync for this repo_id
        # Related to bz700508 - fast sync/cancel_sync locks up task subsystem
        if self.repo_id:
            self.repo_api.set_sync_in_progress(self.repo_id, False)
