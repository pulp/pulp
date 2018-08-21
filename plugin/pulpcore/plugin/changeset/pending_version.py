from pulpcore.plugin.changeset.main import ChangeSet
from pulpcore.plugin.tasking import WorkingDirectory
from pulpcore.plugin.models import RepositoryVersion


class PendingVersion:

    def __init__(self, pending_content, repository, remote, sync_mode='mirror'):
        self.pending_content = pending_content
        self.repository = repository
        self.remote = remote
        self.sync_mode = sync_mode

    def apply(self):
        with WorkingDirectory():
            with RepositoryVersion.create(self.repository) as new_version:
                if self.sync_mode == 'additive':
                    self._additive(new_version)
                elif self.sync_mode == 'mirror':
                    self._mirror(new_version)

    def _additive(self, new_version):
        changeset = ChangeSet(
            self.remote,
            new_version,
            additions=self.pending_content
        )
        [i for i in changeset.apply()]

    def _mirror(self, new_version):
        content_unit_keys_to_remove = [c.cast().natural_key() for c in new_version.content]

        def closure_to_compute_removals():
            for pending_content_item in self.pending_content:
                key = pending_content_item.model.natural_key()
                content_unit_keys_to_remove.remove(key)
                yield pending_content_item

        changeset = ChangeSet(
            self.remote,
            new_version,
            additions=closure_to_compute_removals()
        )
        [i for i in changeset.apply()]
        # TODO  Call into changesets with these removals
        # To have the Changesets handle the removals here, I would have to reconstruct the
        # PendingContent or ContentUnit objects and hand them to the Changeset. It would be easier
        # to do that here directly. At that point that would be redundant with the Changeset's
        # implementation of it also, so that motivates removing 'removals' from the Changeset
        # altogether.
