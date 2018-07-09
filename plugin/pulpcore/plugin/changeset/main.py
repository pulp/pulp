import itertools

from collections.abc import Sized, Iterable
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
        additions (SizedIterable): The content to be added to the repository.
        removals (SizedIterable): The content IDs to be removed.
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
                content should be added and removed
            additions (SizedIterable): The content to be added to the repository.
            removals (SizedIterable): The content IDs to be removed.

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
        log.info(
            _('Apply additions: repository=%(r)s.'),
            {
                'r': self.repository.name
            })

        downloads = DownloadIterator((c.bind(self) for c in self.additions))

        with ProgressBar(message=_('Add Content'), total=len(self.additions)) as bar:
            for artifact, download in downloads:
                content = artifact.content
                try:
                    download.result()
                except Exception as error:
                    task = Task()
                    task.append_non_fatal_error(error)
                    bar.increment()
                    report = ChangeReport(ChangeReport.ADDED, content.model)
                    report.error = error
                    yield report
                else:
                    artifact.settle()
                    content.settle()
                    if not content.settled:
                        continue
                    with transaction.atomic():
                        self._add_content(content)
                        bar.increment()
                    report = ChangeReport(ChangeReport.ADDED, content.model)
                yield report

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
        with ProgressBar(message=_('Remove Content'), total=len(self.removals)) as bar:
            for batch in BatchIterator(self.removals, 1000):
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

        for report in itertools.chain(self._apply_additions(), self._apply_removals()):
            if report.error:
                self.failed += 1
            elif report.action == ChangeReport.ADDED:
                self.added += 1
            else:
                self.removed += 1
            yield report

        log.info(
            _('ChangeSet complete: added:%(a)d, removed:%(r)d, failed:%(f)d'),
            {
                'a': self.added,
                'r': self.removed,
                'f': self.failed
            })

    def apply_and_drain(self):
        """
        Call apply() then iterate and discard the change reports. This is useful when the caller is
        only interested in the added, removed and failed statistics.
        """
        for x in self.apply():
            pass


class SizedIterable(Sized, Iterable):
    """
    A sized iterable.

    Attributes:
        iterable (Iterable): An iterable.
        length (int): The number of items expected to be yielded by the iterable.

    Examples:
        >>>
        >>> generator = (n for n in [1, 2, 3])
        >>> iterable = SizedIterable(generator, 3)
        >>> len(iterable)
        3
        >>> list(iterable)
        [1, 2, 3]
    """

    def __init__(self, iterable, length):
        """
        Args:
            iterable (Iterable): An iterable.
            length (int): The number of items expected to be yielded by the iterable.
        """
        self._iterable = iterable
        self._length = length

    def __len__(self):
        """
        Returns:
            The number of items expected to be yielded by the iterable.
        """
        return self._length

    def __iter__(self):
        return iter(self._iterable)
