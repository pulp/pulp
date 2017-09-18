from collections import namedtuple
import hashlib
import os
import tempfile

from pulpcore.app.models import Artifact
from .exceptions import DigestValidationError, SizeValidationError


DownloadResult = namedtuple('DownloadResult', ['url', 'artifact_attributes', 'path', 'exception'])
"""
Args:
    url (str): The url corresponding with the download.
    path (str): The absolute path to the saved file
    artifact_attributes (dict): Contains keys corresponding with
        :class:`pulpcore.plugin.models.Artifact` fields. This includes the computed digest values
        along with size information.
    exception (Exception): Any downloader exception emitted while the
        :class:`~pulpcore.plugin.download.asyncio.GroupDownloader` is downloading. Otherwise this
        value is `None`.
"""


def attach_url_to_exception(func):
    """
    A decorator that attaches the `url` to any exception emitted by a downloader's `run()` method.

    >>> class MyCustomDownloader(BaseDownloader)
    >>>     @attach_url_to_exception
    >>>     async def run(self):
    >>>         pass  # downloader implementation of run() goes here

    The url is stored on the exception as the `_pulp_url` attribute. This is used by the
    :class:`~pulpcore.plugin.download.asyncio.GroupDownloader` to know the url a given exception
    is for.

    Args:
        func: The method being decorated. This is expected to be the `run()` method of a subclass of
            :class:`~pulpcore.plugin.download.asyncio.BaseDownloader`

    Returns:
        A function that will attach the `url` to any exception emitted by `func`
    """
    async def wrapper(downloader):
        try:
            return await func(downloader)
        except Exception as error:
            error._pulp_url = downloader.url
            raise error
    return wrapper


class BaseDownloader:
    """
    The base class of all downloaders. This is an abstract class and is meant to be subclassed.

    This provides data digest calculation and validation and the writing to a file.

    All subclassed downloaders should pass all downloaded data the into
    :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data` to allow the file digest to
    be computed while data is written to disk. This avoids having to re-read the data later. The
    digests computed are required to save the file as an Artifact, so we need to compute them.

    The :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data` method by default
    writes to a random file in the current working directory or you can pass in your own file
    object. See the ``custom_file_object`` keyword argument for more details. Allowing the download
    instantiator to define the file to receive data allows the streamer to receive the data instead
    of having it written to disk.

    Attributes:
        url (str): The url to download.
        expected_digests (dict): Keyed on the algorithm name provided by hashlib and stores the
            value of the expected digest. e.g. {'md5': '912ec803b2ce49e4a541068d495ab570'}
        expected_size (int): The number of bytes the download is expected to have.
        path (str): The full path to the file containing the downloaded data if no
            ``custom_file_object`` option was specified, otherwise None.
    """

    def __init__(self, url, custom_file_object=None, expected_digests=None, expected_size=None):
        """
        Create a BaseDownloader object. This is expected to be called by all subclasses.

        Args:
            url (str): The url to download.
            custom_file_object (file object): An open, writable file object that downloaded data
                can be written to by
                :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.
            expected_digests (dict): Keyed on the algorithm name provided by hashlib and stores the
                value of the expected digest. e.g. {'md5': '912ec803b2ce49e4a541068d495ab570'}
            expected_size (int): The number of bytes the download is expected to have.
        """
        self.url = url
        if custom_file_object:
            self._writer = custom_file_object
            self.path = None
        else:
            fd, self.path = tempfile.mkstemp(dir=os.getcwd())
            self._writer = os.fdopen(fd, mode='wb')
        self.expected_digests = expected_digests
        self.expected_size = expected_size
        self._digests = {n: hashlib.new(n) for n in Artifact.DIGEST_FIELDS}
        self._size = 0

    def handle_data(self, data):
        """
        Write data to the file object and compute its digests.

        All subclassed downloaders are expected to pass all data downloaded to this method. Similar
        to the hashlib docstring, repeated calls are equivalent to a single call with
        the concatenation of all the arguments: m.handle_data(a); m.handle_data(b) is equivalent to
        m.handle_data(a+b).

        Args:
            data (bytes): The data to be handled by the downloader.
        """
        self._writer.write(data)
        self._record_size_and_digests_for_data(data)

    def _record_size_and_digests_for_data(self, data):
        """
        Record the size and digest for an available chunk of data.

        Args:
            data (bytes): The data to have its size and digest values recorded.
        """
        for algorithm in self._digests.values():
            algorithm.update(data)
        self._size += len(data)

    @property
    def artifact_attributes(self):
        """
        A property that returns a dictionary with size and digest information. The keys of this
        dictionary correspond with :class:`pulpcore.plugin.models.Artifact` fields.
        """
        attributes = {'size': self._size}
        for algorithm in Artifact.DIGEST_FIELDS:
            attributes[algorithm] = self._digests[algorithm].hexdigest()
        return attributes

    def validate_digests(self):
        """
        Validate all digests validate if ``expected_digests`` is set

        Raises:
            :class:`~pulpcore.plugin.download.asyncio.DigestValidationError`: When any of the
                ``expected_digest`` values don't match the digest of the data passed to
                :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.
        """
        if self.expected_digests:
            for algorithm, expected_digest in self.expected_digests.items():
                if expected_digest != self._digests[algorithm].hexdigest():
                    raise DigestValidationError()

    def validate_size(self):
        """
        Validate the size if ``expected_size`` is set

        Raises:
            :class:`~pulpcore.plugin.download.asyncio.SizeValidationError`: When the
                ``expected_size`` value doesn't match the size of the data passed to
                :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.
        """
        if self.expected_size:
            if self._size != self.expected_size:
                raise SizeValidationError()

    async def run(self):
        """
        Run the downloader.

        This is a coroutine that asyncio can schedule to complete downloading. This is required to
        be implemented by subclasses.

        It is expected that the subclass implementation call
        :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.validate_size` and
        :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.validate_digests` after the last
        call to :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data` which will
        validate the data.

        It is also expected that the subclass implementation return a
        :class:`~pulpcore.plugin.download.asyncio.DownloadResult` object. The
        ``artifact_attributes`` value of the
        :class:`~pulpcore.plugin.download.asyncio.DownloadResult` is usually set to the
        :attr:`~pulpcore.plugin.download.asyncio.BaseDownloader.artifact_attributes` property value.

        It is also expected that the subclass implementation be decorated with the
        :class:`~pulpcore.plugin.download.asyncio.attach_url_to_exception` decorator. This is
        required to allow the :class:`~pulpcore.plugin.download.asyncio.GroupDownloader` to properly
        record the exceptions emitted from subclassed downloaders.

        Returns:
            :class:`~pulpcore.plugin.download.asyncio.DownloadResult`

        Raises:
            :class:`~pulpcore.plugin.download.asyncio.DigestValidationError`: When any of the
                ``expected_digest`` values don't match the digest of the data passed to
                :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.
            :class:`~pulpcore.plugin.download.asyncio.SizeValidationError`: When the
                ``expected_size`` value doesn't match the size of the data passed to
                :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.
        """
        raise NotImplementedError('Subclasses must define a run() method that returns a coroutine')
