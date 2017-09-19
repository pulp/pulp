import asyncio
from collections import defaultdict
from contextlib import suppress
from gettext import gettext as _
from itertools import chain

from pulpcore.app.models import Artifact
from pulpcore.plugin.tasking import Task

from .base import DownloadResult
from .factory import DownloaderFactory


class GroupDownloader:
    """
    Download groups of files, with all downloads from all groups occurring in parallel.

    This downloads any number of :class:`~pulpcore.plugin.download.asyncio.Group` objects by adding
    them explicitly using :meth:`~pulpcore.plugin.download.asyncio.GroupDownloader.schedule_group`
    or via an iterator, such as a generator, with
    :meth:`~pulpcore.plugin.download.asyncio.GroupDownloader.schedule_from_iterator`. The generator
    case is useful for limiting the number of in-memory objects.

    This downloader does not raise Exceptions. Instead any exception emitted by the downloader is
    recorded as a non-fatal exception using :meth:`~pulpcore.plugin.Task.append_non_fatal_error`.
    This exception is also recorded on the ``exception`` attribute of the
    :class:`~pulpcore.plugin.download.asyncio.DownloadResult`.

    The Group configures downloaders with the expected size and expected digest values of the
    :class:`~pulpcore.plugin.models.RemoteArtifact`. This ensures that validation errors are
    recorded when the size or digests don't validate.

    Basic Usage:
        >>> downloader = GroupDownloader(importer)
        >>> artifact_a = RemoteArtifact(url=url_a, md5='912ec803b2ce49e4a541068d495ab570')
        >>> artifact_b = RemoteArtifact(url=url_b, size=4172)
        >>> my_group = Group('my_id', [artifact_a, artifact_b])
        >>> downloader.schedule_group(my_group)
        >>> for id, group_results in downloader:
        >>>     print(id)  # id is set to 'my_id'
        >>>     # group_results is a dict of DownloadResult objects keyed by RemoteArtifact

    If you register a large number of groups, you could use a lot of memory holding those objects,
    their associated downloaders, and other related objects. To resolve this, the GroupDownloader
    provides a way to limit the number of effective in-memory objects by processing objects from a
    generator that yields the (id, [RemoteArtifact()]) tuples. See the example below and read the
    schedule_from_iterator() docs for more details.

    Constraining in-memory objects while downloading:
        >>> def group_generator():
        >>>    yield Group('id_1', [RemoteArtifact(url=url_a), RemoteArtifact(url=url_b)])
        >>>    yield Group('id_2', [RemoteArtifact(url=url_a), RemoteArtifact(url=url_b)])
        >>>
        >>> downloader = GroupDownloader(importer)
        >>> downloader.schedule_from_iterator(group_generator)
        >>> for id, group in downloader:
        >>>     print(id)  # id is set to 'id_1'
        >>>     print(group)  # group is the :class:`~pulpcore.plugin.download.asyncio.Group`
    """

    def __init__(self, importer, downloader_overrides=None):
        """
        Args:
            importer (:class:`~pulpcore.plugin.models.Importer`): The importer used to configure
                downloaders with.
            downloader_overrides (dict): The downloader overrides which are passed along to the
                :class:`pulpcore.plugin.downloader.asyncio.DownloaderFactory`
        """
        self.importer = importer

        self.downloader_factory = DownloaderFactory(self.importer,
                                                    downloader_overrides=downloader_overrides)
        self.group_iterator = None
        self.downloads_not_done = set()
        self.groups_not_done = []
        self.urls = defaultdict(list)  # dict with url as the key and a lists of Groups as the value
        self.loop = asyncio.get_event_loop()

    def schedule_from_iterator(self, group_iterator, parallel_group_limit=50):
        """
        Schedule groups to be downloaded using an iterator provided by the user.

        When scheduling groups from the iterator, the ``parallel_group_limit`` argument defines the
        number of groups that are handled in parallel. Once one
        :class:`~pulpcore.plugin.download.asyncio.Group` completes and is returned to the user,
        another one is scheduled which maintains the number of parallel groups until the iterator is
        exhausted.

        When the group_iterator is a generator, this technique limits the effective memory used by
        the :class:`~pulpcore.plugin.models.RemoteArtifact` objects and their associated
        downloaders.

        Additional calls to this will correctly schedule additional iterators, but only the first
        call will specify the `parallel_group_limit`.

        Args:
            group_iterator (iterable): An iterable of
                :class:`~pulpcore.plugin.download.asyncio.Group` objects.
            parallel_group_limit (int): The number of groups to be handled in parallel at any time.
        """
        if self.group_iterator:
            # This is not the first call to schedule an iterable
            self.group_iterator = chain(self.group_iterator, group_iterator)
            return

        self.group_iterator = group_iterator
        for i in range(parallel_group_limit):
            with suppress(StopIteration):
                self.schedule_group(next(self.group_iterator))

    def schedule_group(self, group):
        """
        Schedules a group of `remote_artifacts` for downloading, referred to by an `id`.

        Args:
            group (:class:`~pulpcore.plugin.download.asyncio.Group`): The group to be scheduled.
        """
        self.groups_not_done.append(group)
        for url in group.urls:
            if len(self.urls[url]) == 0:
                # This is the first time we've seen this url so make a downloader
                size_digest_kwargs = self._get_size_digest_kwargs(group.remote_artifacts[url])
                downloader_for_url = self.downloader_factory.build(url, **size_digest_kwargs)
                self.downloads_not_done.add(downloader_for_url)
            self.urls[url].append(group)

    def _get_size_digest_kwargs(self, remote_artifact):
        size_digest_kwargs = {}
        digest_kwargs_only = {}
        if remote_artifact.size:
            size_digest_kwargs['expected_size'] = remote_artifact.size
        for algorithm in Artifact.DIGEST_FIELDS:
            digest_value = getattr(remote_artifact, algorithm)
            if digest_value:
                digest_kwargs_only[algorithm] = digest_value
        if digest_kwargs_only:
            size_digest_kwargs['expected_digests'] = digest_kwargs_only
        return size_digest_kwargs

    def _find_and_remove_done_group(self):
        for index, group in enumerate(self.groups_not_done):
            if group.done:
                self.groups_not_done.pop(index)
                return group

    def __iter__(self):
        return self

    def __next__(self):
        """
        Returns:
            :class:`pulpcore.plugin.download.asyncio.Group`
        """
        while self.downloads_not_done:
            done_this_time, self.downloads_not_done = \
                self.loop.run_until_complete(asyncio.wait(self.downloads_not_done,
                                                          return_when=asyncio.FIRST_COMPLETED))
            with suppress(StopIteration):
                if self.group_iterator:
                    self.schedule_group(next(self.group_iterator))
            for task in done_this_time:
                try:
                    download_result = task.result()
                except Exception as error:
                    msg = _("{exc} for url {url}").format(exc=error, url=error._pulp_url)
                    Task().append_non_fatal_error(Exception(msg))
                    download_result = DownloadResult(url=str(error._pulp_url),
                                                     artifact_attributes=None, path=None,
                                                     exception=error)
                for group in self.urls[download_result.url]:
                    group.handle_download_result(download_result)
                group = self._find_and_remove_done_group()
                if group:
                    return group
        finished_group = self._find_and_remove_done_group()
        if finished_group:
            return finished_group
        else:
            raise StopIteration()


class Group:
    """
    A group of remote_artifacts to download.

    Each group is downloaded with the :class:`~pulpcore.plugin.download.asyncio.GroupDownloader`.

    Attributes:
        id (hashable): This id is used to uniquely identify the group.
        remote_artifacts (dict): Keyed on the remote url with the value containing the
            :class:`~pulpcore.plugin.models.RemoteArtifact`.
        downloaded_files (dict): Keyed on the remote url with the value containing the
             :class:`~pulpcore.plugin.download.asyncio.DownloadResult`
        urls (set): All remote urls in this group.
        finished_urls (list): A list of completed urls.
    """

    def __init__(self, id, remote_artifacts):
        """
        Args:
            id (hashable): This id is used to uniquely identify the group
            remote_artifacts (list): A list of :class:`~pulpcore.plugin.models.RemoteArtifact`
                instances that have not been saved to the database.
        """
        self.id = id
        self.remote_artifacts = {}
        self.downloaded_files = {}
        urls = []
        for remote_artifact in remote_artifacts:
            self.remote_artifacts[remote_artifact.url] = remote_artifact
            urls.append(remote_artifact.url)
        self.urls = set(urls)
        self.finished_urls = []

    def handle_download_result(self, download_result):
        """
        Update the Group with download result calculated during the download from the URL

        Args:
            download_result (:class:`pulpcore.plugin.download.asyncio.DownloadResult`): The return
                argument from an HttpDownloader
        """
        self.finished_urls.append(download_result.url)
        self.downloaded_files[download_result.url] = download_result

    @property
    def done(self):
        """
        A property that returns True if all downloads are completed.

        Returns:
            True if the Group has all downloads completed, False otherwise.
        """
        return len(self.urls) == len(self.finished_urls)
