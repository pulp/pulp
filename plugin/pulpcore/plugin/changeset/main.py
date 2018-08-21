from itertools import chain
from gettext import gettext as _
from logging import getLogger

from django.db import transaction

from ..models import Content, ContentArtifact, RemoteArtifact, ProgressBar
from ..tasking import Task

from .iterator import BatchIterator, DownloadIterator
from .report import ChangeReport


log = getLogger(__name__)


class ChangeSet:
    """
    A set of changes to be applied to a repository.

    When applied, the following changes are made.

    For each content (unit) added:

    - All content artifacts are downloaded as needed (unless deferred=True).
    - The content (model) is saved.
    - All artifacts (models) are saved.
    - Deferred download catalog entries are created for each artifact.
    - The content (unit) is added to the repository.

    For each content (unit) removed:

    - Content removed from the repository.
    - Deferred download catalog deleted for each artifact.

    Attributes:
        remote (pulpcore.plugin.Remote): A remote.
        additions (collections.Iterable): The content to be added to the repository.
        removals (collections.Iterable): The content IDs to be removed.
        added (int): The number of content units successfully added.
        removed (int): The number of content units successfully removed.
        failed (int): The number of changes that failed.
        repository_version (pulpcore.plugin.models.RepositoryVersion): The new version to which
            content should be added and removed

    Examples:
        >>>
        >>> from pulpcore.plugin.changeset import ChangeSet, ChangeFailed
        >>>
        >>> changeset = ChangeSet(...)
        >>> for report in changeset.apply():
        >>>     try:
        >>>         report.result()
        >>>     except ChangeFailed:
        >>>         # failed.  Decide what to do.
        >>>     else:
        >>>         # be happy
        >>>
    """

    def __init__(self, remote, repository_version, additions=(), removals=()):
        """
        Args:
            remote (pulpcore.plugin.models.Remote): A remote.
            repository_version (pulpcore.plugin.models.RepositoryVersion): The new version to which
                content should be added and removed.
            additions (collections.Iterable): The content to be added to the repository.
            removals (collections.Iterable): The content IDs to be removed.

        Notes:
            The content to be added may already exist but not be associated
            to the repository. Existing content is fetched and used instead
            of provided content models as needed.
        """
        self.remote = remote
        self.repository_version = repository_version
        self.additions = additions
        self.removals = removals
        self.added = 0
        self.removed = 0
        self.failed = 0

    @property
    def repository(self):
        """
        The repository being updated.

        Returns:
            pulpcore.plugin.models.Repository: The repository being updated.
        """
        return self.repository_version.repository

    def _add_content(self, content):
        """
        Add the specified content to the repository.
        Download catalog entries are created foreach artifact.

        Args:
            content (PendingContent): The content to be added.
        """
        with transaction.atomic():
            self.repository_version.add_content(
                Content.objects.filter(pk=content.stored_model.id))

    def _remove_content(self, content):
        """
        Remove content from the repository.
        Download catalog entries are deleted foreach artifact.

        Args:
            content (pulpcore.plugin.Content): A content model to be removed.
        """
        q_set = RemoteArtifact.objects.filter(
            remote=self.remote,
            content_artifact__in=ContentArtifact.objects.filter(content=content))
        q_set.delete()
        with transaction.atomic():
            self.repository_version.remove_content(content)

    def _apply_additions(self):
        """
        Apply additions.
        Content listed in `additions` is created (as needed) and added to the repository.

        Yields:
            ChangeReport: A report for each content added.
        """
        def completed():
            content = artifact.content
            try:
                download.result()
            except Exception as error:
                task = Task()
                task.append_non_fatal_error(error)
                add_bar.increment()
                return ChangeReport(ChangeReport.ADDED, content.model, error=error)
            else:
                artifact.settle()
                content.settle()
                if not content.settled:
                    return
                with transaction.atomic():
                    self._add_content(content)
                    add_bar.increment()
                return ChangeReport(ChangeReport.ADDED, content.model)

        log.info(
            _('Apply additions: repository=%(r)s.'),
            {
                'r': self.repository.name
            })

        add_bar = ProgressBar(message=_('Add Content'), total=0)
        download_bar = ProgressBar(message=_('Download Artifact'), total=0)

        with add_bar, download_bar:
            additions = (c.bind(self) for c in self.additions)
            for batch in BatchIterator(additions):
                add_bar.total += len(batch)
                add_bar.save()
                for artifact, download in DownloadIterator(batch, bar=download_bar):
                    yield completed()

    def _apply_removals(self):
        """
        Apply removals.
        Content listed in `removals` is removed from the repository.

        Yields:
            ChangeReport: A report for each removed content.
        """
        log.info(
            _('Apply removals: repository=%(r)s.'),
            {
                'r': self.repository.name
            })

        with ProgressBar(message=_('Remove Content'), total=0) as bar:
            for batch in BatchIterator(self.removals):
                bar.total += len(batch)
                bar.save()
                with transaction.atomic():
                    for content in batch:
                        self._remove_content(content)
                        bar.done += len(batch)
                        bar.save()
                        report = ChangeReport(ChangeReport.REMOVED, content)
                        yield report

    def apply(self):
        """
        Apply the requested changes to the repository.

        Yields:
            ChangeReport: For each change applied.
        """
        log.info(
            _('Apply ChangeSet: repository=%(r)s.'),
            {
                'r': self.repository.name
            })

        self.added = 0
        self.removed = 0
        self.failed = 0

        for report in chain(self._apply_additions(), self._apply_removals()):
            if report.error:
                self.failed += 1
                continue
            if report.action == ChangeReport.ADDED:
                self.added += 1
                continue
            if report.action == ChangeReport.REMOVED:
                self.removed += 1
            yield report

        log.info(
            _('ChangeSet applied: added:%(a)d, removed:%(r)d, failed:%(f)d'),
            {
                'a': self.added,
                'r': self.removed,
                'f': self.failed
            })
