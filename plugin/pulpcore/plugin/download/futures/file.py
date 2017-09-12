from errno import ENOENT, EPERM
from urllib.parse import urlparse

from .error import DownloadFailed, NotFound, NotAuthorized
from .single import Download


# ERRNO mapped to standard exception.
ERROR = {
    ENOENT: NotFound,
    EPERM: NotAuthorized
}


class FileDownload(Download):
    """
    Local File download.
    Handles the file:// protocol.

    Attributes:
        error (int): Status code. (0 = OK, else set to ERRNO)

    Examples:
        >>>
        >>> from pulpcore.plugin.download.futures import DownloadError, FileDownload, FileWriter
        >>>
        >>> url = ...
        >>> path = ...
        >>>
        >>> download = FileDownload(url, FileWriter(path))
        >>>
        >>> try:
        >>>     download()
        >>> except DownloadError:
        >>>     # An error occurred.
        >>> else:
        >>>     # Go read the downloaded file \o/
    """

    __slots__ = ('error',)

    def __init__(self, url, writer):
        """
        Args:
            url (str): A file download URL.
            writer (Writer): An object used to store downloaded file.
        """
        super(FileDownload, self).__init__(url, writer)
        self.error = 0

    def _send(self):
        """
        Read the file.

        Raises:
            DownloadFailed: The download failed and could not be repaired.
        """
        try:
            path = urlparse(self.url).path
            with open(path, 'rb') as fp:
                while True:
                    buffer = fp.read(self.BLOCK)
                    if buffer:
                        self._write(buffer)
                    else:
                        break
        except OSError as error:
            raise ERROR.get(error.errno, DownloadFailed)(self, str(error))
