import itertools
from collections.abc import Sized, Iterable
from gettext import gettext as _
from logging import getLogger

from django.db.utils import IntegrityError
from django.db import transaction

from ..download.futures import Batch
from ..models import ContentArtifact, RemoteArtifact, ProgressBar, RepositoryContent
from ..tasking import Task

from .iterator import ArtifactIterator, BatchIterator, ContentIterator, DownloadIterator
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
        importer (pulpcore.plugin.Importer): An importer.
        additions (SizedIterable): The content to be added to the repository.
        removals (SizedIterable): The content IDs to be removed.
        deferred (bool): Downloading is deferred.  When true, downloads are not performed
            but content is still created and added to the repository.
        added (int): The number of content units successfully added.
        removed (int): The number of content units successfully removed.
        failed (int): The number of changes that failed.

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

    def __init__(self, importer, additions=(), removals=()):
        """
        Args:
            importer (pulpcore.plugin.Importer): An importer.
            additions (SizedIterable): The content to be added to the repository.
            removals (SizedIterable): The content IDs to be removed.

        Notes:
            The content to be added may already exist but not be associated
            to the repository. Existing content is fetched and used instead
            of provided content models as needed.
        """
        self.importer = importer
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
        return self.importer.repository

    def _downloads(self):
        """
        Get an iterable (flattened) of download objects for all pending artifacts.
        Builds an iterator chain which provides streams-processing of the pending content
        and related artifacts.  Each iterator in the chain has logic for transforming
        the objects being iterated.  See each iterator for details.

        Returns:
            DownloadIterator: An iterable of download objects.
        """
        content = ContentIterator((c.bind(self) for c in self.additions))
        artifacts = ArtifactIterator(content)
        downloads = DownloadIterator(artifacts, self.importer.is_deferred)
        return downloads

    def _add_content(self, content):
        """
        Add the specified content to the repository.
        Download catalog entries are created foreach artifact.

        Args:
            content (PendingContent): The content to be added.
        """
        try:
            association = RepositoryContent(
                repository=self.importer.repository,
                content=content.model)
            association.save()
        except IntegrityError:
            # Duplicate
            pass

    def _remove_content(self, content):
        """
        Remove content from the repository.
        Download catalog entries are deleted foreach artifact.

        Args:
            content (pulpcore.plugin.Content): A content model to be removed.
        """
        q_set = RemoteArtifact.objects.filter(
            importer=self.importer,
            content_artifact__in=ContentArtifact.objects.filter(content=content))
        q_set.delete()
        q_set = RepositoryContent.objects.filter(
            repository=self.repository,
            content=content)
        q_set.delete()

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
        with Batch(self._downloads()) as batch:
            with ProgressBar(message=_('Add Content'), total=len(self.additions)) as bar:
                for plan in batch():
                    artifact = plan.download.attachment
                    content = artifact.content
                    try:
                        plan.result()
                    except Exception as error:
                        task = Task()
                        task.append_non_fatal_error(error)
                        bar.increment()
                        report = ChangeReport(ChangeReport.ADDED, content.model)
                        report.error = plan.error
                        yield report
                        continue
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
