import asyncio
import itertools

from collections.abc import Iterable
from logging import getLogger

from django.db.models import Q

from pulpcore.app.models import Artifact

from .model import NopPendingArtifact


log = getLogger(__name__)


class BatchIterator(Iterable):
    """
    Iterate large numbers of items in batches.

    Attributes:
        iterable (Iterable): An iterable to batch.
        batch (int): The size of each batch.

    Examples:
        >>>
        >>> numbers = [1, 2, 3, 4, 5, 6]
        >>> for batch in BatchIterator(numbers, 3):
        >>>     repr(batch)
        '(1, 2, 3)'
        '(4, 5, 6)'
    """

    # Default batch size.
    BATCH = 1000

    def __init__(self, iterable, batch=BATCH):
        """
        Args:
            iterable (Iterable): An iterable to batch.
            batch (int): The size of each batch.
        """
        self.iterable = iterable
        self.batch = batch

    def __iter__(self):
        generator = (c for c in self.iterable)
        while True:
            batch = tuple(itertools.islice(generator, 0, self.batch))
            if batch:
                yield batch
            else:
                return


class ContentIterator(Iterable):
    """
    Iterate `PendingContent` and foreach, replace the DB model instance
    with an instance fetched from the DB (when found).

    Attributes:
        content (iterable): An iterable of PendingContent.
    """

    @staticmethod
    def _batch_q(content):
        """
        Build a query for the specified batch of content.

        Args:
            content (tuple): A batch of content.  Each is: PendingContent.

        Returns:
            Q: The built query.
        """
        q = Q()
        for c in content:
            q |= Q(**c.key)
        return q

    def __init__(self, content):
        """
        Args:
            content (iterable): An iterable of PendingContent.
        """
        self.content = content

    def _collated_content(self):
        """
        Collate each batch of content into lists by model.

        Yields:
            dict: A dictionary of {model_class: [content,]}
                Each content is: PendingContent.
        """
        for batch in BatchIterator(self.content, 1024):
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
                The content is a list of PendingContent.
                The fetched is a dictionary of fetched content models keyed by natural key.
        """
        for collated in self._collated_content():
            for model, content in collated.items():
                q = self._batch_q(content)
                q_set = model.objects.filter(q)
                q_set = q_set.only(*model.natural_key_fields())
                fetched = {c.natural_key(): c for c in q_set}
                yield (content, fetched)

    def _iter(self):
        """
        The pending content is iterated and its model is replaced with a model
        fetched from the DB (when found). This is batched to limit the memory
        footprint.

        Yields:
            PendingContent: The transformed content.
        """
        for batch, fetched in self._fetch():
            for content in batch:
                natural_key = content.model.natural_key()
                try:
                    model = fetched[natural_key]
                except KeyError:
                    pass
                else:
                    content.stored_model = model
                yield content

    def __iter__(self):
        return iter(self._iter())


class ArtifactIterator(Iterable):
    """
    Iterate `PendingContent` and foreach artifact, replace the DB model instance
    with an instance fetched from the DB (when found).  Ensure that at
    least (1) artifact is yielded for each content.

    Attributes:
        content (iterable): An iterable of PendingContent.
    """

    def __init__(self, content):
        """
        Args:
            content (iterable): An iterable of PendingContent.
        """
        self.content = content

    @staticmethod
    def _batch_q(artifacts):
        """
        Build a query for the specified batch of artifacts.

        Args:
            artifacts (tuple): A batch of artifacts.  Each is: PendingArtifact.

        Returns:
            Q: The built query.
        """
        q = Q()
        for artifact in (a for a in artifacts if not isinstance(a, NopPendingArtifact)):
            q |= artifact.artifact_q()
        return q

    def _batch_artifacts(self):
        """
        Build a flattened collection of pending artifacts.
        A NopPendingArtifact is yielded when the content has no artifacts.

        Returns:
            BatchIterator: Flattened iterable of PendingArtifact.
        """
        def build():
            for content in self.content:
                if content.artifacts:
                    for artifact in content.artifacts:
                        artifact.content = content
                        yield artifact
                else:
                    yield NopPendingArtifact(content)
        return BatchIterator(build(), 1024)

    @staticmethod
    def _set_stored_model(fetched, artifact):
        """
        Set the stored_model on the artifact with the model matched in the cache.
        The artifact is matched by digest by order of algorithm strength.

        The cache key is (tuple): (field, digest).

        Args:
            fetched (dict): Artifacts fetched from the DB.
                Keyed with (field, digest)
            artifact (pulpcore.plugin.changeset.PendingArtifact): A pending artifact.

        """
        if isinstance(artifact, NopPendingArtifact):
            return
        for field in Artifact.RELIABLE_DIGEST_FIELDS:
            digest = getattr(artifact.model, field)
            if not digest:
                continue
            key = (field, digest)
            model = fetched.get(key)
            if model:
                artifact.stored_model = model
                break

    def _iter(self):
        """
        Iterate the content and flatten the artifacts.
        Ensure that at least (1) artifact is yielded for each content. When content
        does not have any un-downloaded artifacts, A NopPendingArtifact is yielded.
        The PendingArtifact.artifact set with an Artifact fetched from DB.  This is
        batched to limit the memory footprint.

        Yields:
            pulpcore.plugin.changeset.PendingArtifact: The flattened pending artifacts.
        """
        for batch in self._batch_artifacts():
            q = self._batch_q(batch)
            fetched = {}
            for model in Artifact.objects.filter(q):
                for field in Artifact.RELIABLE_DIGEST_FIELDS:
                    digest = getattr(model, field)
                    key = (field, digest)
                    fetched[key] = model
            for artifact in batch:
                self._set_stored_model(fetched, artifact)
                yield artifact

    def __iter__(self):
        return iter(self._iter())


class DownloadIterator(Iterable):
    """
    Download pending artifacts.

    Attributes:
        content (pulpcore.plugin.changeset.PendingContent): Pending content to be iterated.
    """

    # The (default) number of concurrent downloads.
    CONCURRENT = 10

    def __init__(self, content, concurrent=CONCURRENT):
        """
        Args:
            content (Iterable): Pending content to be iterated.
            concurrent (int): The number of concurrent downloads.
        """
        self.content = content
        self.concurrent = concurrent

    def _iter(self):
        """
        Build the iterator pipeline:
            ContentIterator => ArtifactIterator => Downloader.
        Then, execute each downloader (coroutine).

        Yields:
            tuple: Completed downloads:
              * pulpcore.plugin.changeset.PendingArtifact
              * asyncio.Future.
        """
        content = ContentIterator(self.content)
        artifacts = ArtifactIterator(content)
        loop = asyncio.get_event_loop()
        downloads = ((a, a.downloader) for a in artifacts)
        for batch in BatchIterator(downloads, self.concurrent):
            correlation = {d: a for a, d in batch}
            pending = correlation.keys()
            while pending:
                future = asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                completed, pending = loop.run_until_complete(future)
                for task in completed:
                    artifact = correlation[task]
                    yield (artifact, task)

    def __iter__(self):
        return iter(self._iter())
