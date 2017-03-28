import itertools

from gettext import gettext as _
from logging import getLogger

from django.db.models import Q
from django.db.utils import IntegrityError
from django.core.files import File

from pulp.app.models import ProgressBar, DownloadCatalog, RepositoryContent
from pulp.download import Batch, Download

from .tasking import Task


log = getLogger(__name__)


class Remote:
    """
    Represents content related things contained within the remote repository but
    is not contained within the local (pulp) repository.

    Attributes:
        model (Model): A remote (wanted) model object.
        dirty (bool): The model object is has changed and needs to be saved.
    """

    def __init__(self, model):
        """
        Args:
            model (Model): A remote (wanted) model object.
        """
        self.model = model
        self.dirty = True

    def save(self):
        """
        Save the model object only when dirty.
        """
        if not self.dirty:
            return
        self.model.save()
        log.debug(_('Saved'))


class RemoteContent(Remote):
    """
    Represents content contained within the remote repository but is not
    contained within the local (pulp) repository.

    Attributes:
        model (pulp.plugin.Content): A real content model object.
        settled (bool): Indicates that all artifacts have been downloaded
            and the content is ready to be imported.

        _artifacts (set): The set of related `RemoteArtifact`.
    """

    def __init__(self, model):
        """
        Args:
            model (pulp.plugin.Content): A real content model object.

        """
        super(RemoteContent, self).__init__(model)
        self._artifacts = set()
        self.settled = False

    @property
    def artifacts(self):
        """
        Associated artifacts (read only).

        Returns:
            frozenset: Associated artifacts.
        """
        return frozenset(self._artifacts)

    def add_artifact(self, artifact):
        """
        Add a remote artifact.

        Args:
            artifact(RemoteArtifact): An artifact to add.
        """
        artifact.content = self
        self._artifacts.add(artifact)

    def update(self, model):
        """
        Update this `model` stored with the specified model that has been
        fetched from the database. The artifacts are matched by `relative_path`
        and their model object is replaced by the fetched model.

        Args:
            model (pulp.plugin.Content): A fetched content model object.
        """
        self.model = model
        known = {a.model.relative_path: a for a in self._artifacts}
        self._artifacts.clear()
        for artifact in model.artifacts:
            try:
                found = known[artifact.relative_path]
                found.model = artifact
                self._artifacts.add(found)
            except KeyError:
                log.error(_('Artifact not matched.'))

    def settle(self):
        """
        Settle matters that are prerequisite to associating the wrapped content
        with a repository.  This mainly pertains to the artifacts being downloaded;
        and associated artifact models saved; the wrapped content model saved.

        Notes:
            Called whenever an artifact has been downloaded.
        """
        for artifact in self._artifacts:
            if not artifact.model.downloaded:
                return
        try:
            self.save()
            for artifact in self._artifacts:
                artifact.model.content = self.model
                artifact.model.file = File(open(artifact.download.path, mode='rb'))
                artifact.save()
            self.settled = True
        except Exception:
            log.exception(_('Settle Failed.'))

    def save(self):
        """
        Save the content model only when needed.
        """
        if not self.dirty:
            return
        try:
            self.model.save()
        except IntegrityError:
            key = {f: getattr(self.model, f) for f in self.model.natural_key_fields}
            model = self.model.objects.get(**key)
            self.update(model)


class RemoteArtifact(Remote):
    """
    Represents an artifact related to content contained within the remote
    repository is not contained within the local (pulp) repository.

    Attributes:
        download (pulp.download.Download): An object used to download the content.
        content (RemoteContent): The associated remote content.
        catalog (Catalog): A deferred download catalog.
    """

    def __init__(self, model, download):
        """

        Args:
            model (pulp.plugin.Artifact): An artifact model object.
            download (pulp.download.Download): A An object used to download the content.
        """
        super(RemoteArtifact, self).__init__(model)
        self.download = download
        download.attachment = self
        self.content = None
        self.catalog = None

    def save(self):
        """
        Save and add deferred catalog entry.
        """
        super(RemoteArtifact, self).save()
        self.catalog.add(self)

    def __hash__(self):
        return hash(self.model.id)


class SizedIterator:
    """
    An iterator for a generator when the number of items yielded
    by the generator is known.
    """

    def __init__(self, length, generator):
        """
        Args:
            length (int): The number of items expected to be yielded by the generator.
            generator: A generator.
        """
        self.length = length
        self.generator = generator

    def __len__(self):
        """
        Returns:
            The number of items expected to be yielded by the generator.
        """
        return self.length

    def __iter__(self):
        return iter(self.generator)


class ChangeSet:
    """
    A set of changes to be applied to a repository.

    Attributes:
        importer (pulp.plugin.Importer): An importer.
        adds (SizedIterator): The content to be added to the repository.
        deletes (SizedIterator): The content to be deleted.

    Examples:

            >>>
            >>> # TODO: Add example.
            >>>
    """

    def __init__(self, importer, adds, deletes):
        """
        Args:
            importer (pulp.plugin.Importer): An importer.
            adds (generator): The content to be added to the repository.
            deletes (generator): The content to be deleted.

        Notes:
            The content to be added may already exist but not be associated
            to the repository. Existing content is fetched and used instead
            of provided content models as needed.
        """
        self.importer = importer
        self.adds = adds
        self.deletes = deletes

    @property
    def download_deferred(self):
        return self.importer.download_policy != "immediate"

    def _associate(self, content):
        """
        Associate content.

        Args:
            content (RemoteContent): The content to be associated.
        """
        log.debug(_('Associate content.'))
        try:
            association = RepositoryContent(
                repository=self.importer.repository,
                content=content)
            association.save()
        except IntegrityError:
            # Duplicate
            pass

    def _disassociate(self, content):
        """
        (Un)associate content with the repository.

        Args:
            content (pulp.plugin.Content): A content model to be unassociated.
        """
        log.debug(_('Un-associate content.'))
        RepositoryContent.objects.delete(
            repository=self.importer.repository,
            content=content)
        for artifact in content.artifacts:
            DownloadCatalog.objects.delete(
                importer=self.importer,
                artifact=artifact)

    def _add_content(self):
        """
        Add wanted content.

        Yields:
            AddReport: A report for each content added.
        """
        activity = _('Adding content')
        log.info(activity)

        catalog = Catalog(self.importer)
        with Batch(DownloadIterator(self.adds, self.download_deferred)) as batch:
            with ProgressBar(activity, len(self.adds)) as bar:
                for plan in batch():
                    if not plan.succeeded:
                        task = Task()
                        task.append_non_fatal_error(plan.error)
                        continue
                    artifact = plan.download.attachment
                    artifact.dirty = True
                    artifact.model.downloaded = True
                    artifact.catalog = catalog
                    content = artifact.content
                    content.settle()
                    if not content.settled:
                        continue
                    self._associate(content.model)
                    bar.increment()
                    report = AddReport(content.model)
                    yield report

    def _delete_content(self):
        """
        Delete unwanted content.

        Yields:
            DeleteReport: A report for each removed content.
        """
        activity = _('Removing content.')
        log.info(activity)

        with ProgressBar(activity, len(self.deletes)) as bar:
            for content in self.deletes:
                self._disassociate(content)
                bar.increment()
                report = DeleteReport(content)
                yield report

    def apply(self):
        """
        Apply the changes to the repository based on download policy.

        Yields:
            ChangeReport: For each change applied.
        """
        log.info(_('Apply'))
        for report in self._add_content():
            yield report
        for report in self._delete_content():
            yield report


class ChangeReport:
    """
    Report changes to a repository.

    Attributes:
        action (str): The action taken (ADD, DEL).
        content (pulp.plugin.Content): The affected content model.
    """

    ADDED = 'ADD'
    DELETED = 'DEL'

    def __init__(self, action, content):
        """
        Args:
            action (str): The action taken (ADD, DEL).
            content (pulp.plugin.Content): The affected content model.

        """
        self.action = action
        self.content = content


class AddReport(ChangeReport):
    """
    Report of added content.
    """

    def __init__(self, content):
        """
        Args:
            content (pulp.plugin.Content): The added content model.
        """
        super(AddReport, self).__init__(self.ADDED, content)


class DeleteReport(ChangeReport):
    """
    Report of removed content.
    """

    def __init__(self, content):
        """
        Args:
            content (pulp.plugin.Content): The removed content model.
        """
        super(DeleteReport, self).__init__(self.DELETED, content)


class TransformingIterator:
    """
    An iterator used to do inline (stream) filtering and transformation of a collection.

    Attributes:
        collection (iterable): An iterable to be filtered and iterated.

    Notes:
        In most cases, the `collection` is a generator.
    """

    def __init__(self, collection):
        """
        Args:
            collection (iterable): An iterable to be filtered and iterated.

        """
        self.collection = collection

    def filter(self):
        """
        Yield filtered items in the collection.

        Yields:
            filtered items in the collection.

        Notes:
            Must be overridden by subclasses.
        """
        raise NotImplementedError()

    def __iter__(self):
        return iter(self.filter())


class ContentIterator(TransformingIterator):
    """
    Iterate a generator of `RemoteContent` and replace associated content models
    With models fetched from the DB (when found).
    """

    # Number of keys in each batched query.
    BATCH = 1024

    @staticmethod
    def _batch_q(content):
        """
        Build a query for the specified batch of content.

        Args:
            content (tuple): A batch of content.  Each is: RemoteContent.

        Returns:
            Q: The built query.
        """
        query = Q()
        for c in content:
            key = {f: getattr(c.model, f) for f in c.model.natural_key_fields}
            query = query | Q(**key)
        return query

    def _batch_content(self, size=BATCH):
        """
        Slice the content into batches.

        Args:
            size (int, optional): The number of content in each batch.

        Yields:
            tuple: Each batch of: RemoteContent.
        """
        content = (c for c in self.collection)
        while True:
            batch = tuple(itertools.islice(content, 0, size))
            if batch:
                yield batch
            else:
                return

    def _collated_content(self):
        """
        Collate each batch of content into lists by model.

        Yields:
            dict: A dictionary of {model_class: [content,]}
                Each content is: RemoteContent.
        """
        for batch in self._batch_content():
            collated = {}
            for content in batch:
                _list = collated.setdefault(type(content.model), list())
                _list.append(content)
            yield collated

    def _fetch(self):
        """
        Fetch each batch of collated content.

        Yields:
            tuple: (content, fetched).
                The content is a list of RemoteContent.
                The fetched is a dictionary of fetched content models keyed by natural key.
        """
        for collated in self._collated_content():
            for model, content in collated.items():
                fields = [
                    'artifacts'
                ]
                fields.extend(model.natural_key_fields)
                q = self._batch_q(content)
                q_set = model.objects.filter(q)
                q_set = q_set.only(fields)
                fetched = {c.natural_key(): c for c in q_set}
                yield (content, fetched)

    def filter(self):
        """
        Iterate and filter.

        Yields:
            RemoteContent: The filtered content.
        """
        for batch, fetched in self._fetch():
            for content in batch:
                natural_key = content.model.natural_key()
                try:
                    model = fetched[natural_key]
                except KeyError:
                    pass
                else:
                    content.update(model)
                    content.dirty = False
                    for artifact in content.artifacts:
                        artifact.dirty = False
                yield content


class DownloadIterator(TransformingIterator):
    """
    Iterate the content artifacts and yield the appropriate download object.
    When downloading is deferred or the artifact is already downloaded,
    A NopDownload is yielded.
    """

    def __init__(self, adds, deferred=False):
        """
        Args:
            adds: The collection of wanted content.
            deferred (bool): When true, downloading is deferred.
        """
        super(DownloadIterator, self).__init__(adds)
        self.deferred = deferred

    def filter(self):
        """
        Iterate the content artifacts and yield the appropriate download object.
        When downloading is deferred or the artifact is already downloaded,
        A NopDownload is yielded.

        Yields:
            Download: The appropriate download object.
        """
        for artifact in ArtifactIterator(self.collection):
            if self.deferred or artifact.model.downloaded:
                download = NopDownload()
                download.attachment = artifact
            else:
                download = artifact.download
            yield download


class ArtifactIterator(TransformingIterator):
    """
    Iterate the content and flatten the artifacts.
    Ensure that at least (1) artifact is yielded for each content.
    """

    def filter(self):
        """
        Iterate the content and flatten the artifacts.
        Ensure that at least (1) artifact is yielded for each content. When content
        does not have any un-downloaded artifacts, A NopArtifact is yielded.

        Yields:
            RemoteArtifact: The flattened artifacts.
        """
        for content in ContentIterator(self.collection):
            if content.artifacts:
                for artifact in content.artifacts:
                    yield artifact
            else:
                artifact = RemoteArtifact(NopArtifact(), NopDownload())
                artifact.content = content
                yield artifact


class Catalog:
    """
    Deferred download catalog.
    """

    def __init__(self, importer):
        """
        Args:
            importer (pulp.plugin.Importer): An importer.
        """
        self.importer = importer

    def add(self, artifact):
        """
        Add deferred catalog entries for content being added.

        Args:
            artifact (RemoteArtifact): An artifact to be cataloged.
        """
        log.info(_('Cataloging: {a}').format(a=self))
        try:
            entry = DownloadCatalog()
            entry.importer = self.importer
            entry.url = artifact.download.url
            entry.artifact = artifact.model
            entry.save()
        except IntegrityError:
            # Duplicate
            pass


class NopDownload(Download):
    """
    A no-operation (NOP) download.
    """

    def __init__(self):
        super(NopDownload, self).__init__('', '')

    def _send(self):
        return self

    def __call__(self):
        pass


class NopArtifact:
    """
    No operation (NOP) artifact model.
    """

    def __init__(self):
        self.downloaded = True
