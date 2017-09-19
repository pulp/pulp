import os
from urllib.parse import urlparse

from .base import attach_url_to_exception, BaseDownloader, DownloadResult


class FileDownloader(BaseDownloader):
    """
    A downloader for downloading files from the filesystem.

    It provides digest and size validation along with computation of the digests needed to save the
    file as an Artifact. It writes a new file to the disk and the return path is included in the
    :class:`~pulpcore.plugin.download.asyncio.DownloadResult`.

    This downloader has all of the attributes of
    :class:`~pulpcore.plugin.download.asyncio.BaseDownloader`
    """

    def __init__(self, url, **kwargs):
        """
        Download files from a url that starts with `file://`

        Args:
            url (str): The url to the file. This is expected to begin with `file://`
            kwargs (dict): This accepts the parameters of
                :class:`~pulpcore.plugin.download.asyncio.BaseDownloader`.
        """
        p = urlparse.urlparse(url)
        self._path = os.path.abspath(os.path.join(p.netloc, p.path))
        super().__init__(url, **kwargs)

    @attach_url_to_exception
    async def run(self):
        """
        Read, validate, and compute digests on the `url`. This is a coroutine.

        This method provides the same return object type and documented in
        :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.run`.
        """
        with open(self._path, 'r') as f_handle:
            while True:
                chunk = await f_handle.read(1024)
                if not chunk:
                    self.finalize()
                    break  # the reading is done
                self.handle_data(chunk)
            return DownloadResult(path=self._path, artifact_attributes=self.artifact_attributes,
                                  url=self.url, exception=None)
