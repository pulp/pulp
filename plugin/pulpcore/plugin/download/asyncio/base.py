import asyncio
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
        :class:`~pulpcore.plugin.models.Artifact` fields. This includes the computed digest values
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
    The base class of all downloaders, providing digest calculation, validation, and file handling.

    This is an abstract class and is meant to be subclassed. Subclasses are required to implement
    the :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.run` method and do two things:

        1. Pass all downloaded data to
           :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.

        2. Call :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.finalize` after all data has
           been delivered to :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.

    Passing all downloaded data the into
    :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data` allows the file digests to
    be computed while data is written to disk. The digests computed are required if the download is
    to be saved as an :class:`~pulpcore.plugin.models.Artifact` which avoids having to re-read the
    data later.

    The :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data` method by default
    writes to a random file in the current working directory or you can pass in your own file
    object. See the ``custom_file_object`` keyword argument for more details. Allowing the download
    instantiator to define the file to receive data allows the streamer to receive the data instead
    of having it written to disk.

    The call to :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.finalize` ensures that all
    data written to the file-like object is quiesced to disk before the file-like object has
    `close()` called on it.

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
            self._writer = tempfile.NamedTemporaryFile(dir=os.getcwd(), delete=False)
            self.path = self._writer.name
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

    def finalize(self):
        """
        Flush downloaded data, close the file writer, and validate the data.

        All subclasses are required to call this method after all data has been passed to
        :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.

        Raises:
            :class:`~pulpcore.plugin.download.asyncio.DigestValidationError`: When any of the
                ``expected_digest`` values don't match the digest of the data passed to
                :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.
            :class:`~pulpcore.plugin.download.asyncio.SizeValidationError`: When the
                ``expected_size`` value doesn't match the size of the data passed to
                :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.
        """
        self._writer.flush()
        os.fsync(self._writer.fileno())
        self._writer.close()
        self.validate_digests()
        self.validate_size()

    def fetch(self):
        """
        Run the download synchronously and return the `DownloadResult`.

        Returns:
            :class:`~pulpcore.plugin.download.asyncio.DownloadResult`

        Raises:
            Exception: Any fatal exception emitted during downloading
        """
        done, _ = asyncio.get_event_loop().run_until_complete(asyncio.wait([self.run()]))
        return done.pop().result()

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
        dictionary correspond with :class:`~pulpcore.plugin.models.Artifact` fields.
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

        This is a coroutine that asyncio can schedule to complete downloading. Subclasses are
        required to implement this method and do two things:

        1. Pass all downloaded data to
           :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.

        2. Call :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.finalize` after all data has
           been delivered to :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.handle_data`.

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
            Validation errors could be emitted when subclassed implementations call
            :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.finalize`.
        """
        raise NotImplementedError('Subclasses must define a run() method that returns a coroutine')
