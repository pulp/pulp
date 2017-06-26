import itertools

from collections.abc import Iterable
from logging import getLogger

from django.db.models import Q

from pulpcore.download import Download

from .model import RemoteArtifact


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
    Iterate `RemoteContent` and replace associated content models
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
        q = Q()
        for c in content:
            q |= Q(**c.key)
        return q

    def __init__(self, content):
        """
        Args:
            content (Iterable): An Iterable of RemoteContent.
        """
        self.content = content

    def _collated_content(self):
        """
        Collate each batch of content into lists by model.

        Yields:
            dict: A dictionary of {model_class: [content,]}
                Each content is: RemoteContent.
        """
        for batch in BatchIterator(self.content, self.BATCH):
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
                fields = {f.name for f in model.natural_key_fields}
                q = self._batch_q(content)
                q_set = model.objects.filter(q)
                q_set = q_set.only(*fields)
                fetched = {c.natural_key(): c for c in q_set}
                yield (content, fetched)

    def _iter(self):
        """
        The remote content is iterated and its model is replaced with a model
        fetched from the DB (when found). This is batched to limit the memory
        footprint.

        Yields:
            RemoteContent: The transformed content.
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
                yield content

    def __iter__(self):
        return iter(self._iter())


class DownloadIterator(Iterable):
    """
    Iterate the content artifacts and yield the appropriate download object.
    When downloading is deferred or the artifact is already downloaded,
    A NopDownload is yielded.
    """

    def __init__(self, content, deferred=False):
        """
        Args:
            content (Iterable): An Iterable of RemoteContent.
            deferred (bool): When true, downloading is deferred.
        """
        self.content = content
        self.deferred = deferred

    def _iter(self):
        """
        Iterate the content artifacts and yield the appropriate download object.
        When downloading is deferred or the artifact is already downloaded,
        A NopDownload is yielded.

        Yields:
            Download: The appropriate download object.
        """
        for artifact in ArtifactIterator(self.content):
            if self.deferred or artifact.model.downloaded:
                download = NopDownload()
                download.attachment = artifact
                artifact.path = None
            else:
                download = artifact.download
            yield download

    def __iter__(self):
        return iter(self._iter())


class ArtifactIterator(Iterable):
    """
    Iterate the content and flatten the artifacts.
    Ensure that at least (1) artifact is yielded for each content.
    """

    def __init__(self, content):
        """
        Args:
            content (Iterable): An Iterable of RemoteContent.
        """
        self.content = content

    def _iter(self):
        """
        Iterate the content and flatten the artifacts.
        Ensure that at least (1) artifact is yielded for each content. When content
        does not have any un-downloaded artifacts, A NopArtifact is yielded.

        Yields:
            RemoteArtifact: The flattened artifacts.
        """
        for content in ContentIterator(self.content):
            if content.artifacts:
                for artifact in content.artifacts:
                    artifact.content = content
                    yield artifact
            else:
                artifact = RemoteArtifact(NopArtifact(), NopDownload())
                artifact.content = content
                yield artifact

    def __iter__(self):
        return iter(self._iter())


class NopDownload(Download):
    """
    A no-operation (NOP) download.
    """

    def __init__(self):
        super(NopDownload, self).__init__('', None)

    def _send(self):
        pass

    def __call__(self):
        pass


class NopArtifact:
    """
    No operation (NOP) artifact model.
    """

    def __init__(self):
        self.downloaded = True
