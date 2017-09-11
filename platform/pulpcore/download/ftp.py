from ftplib import FTP
from urllib.parse import urlparse

from .single import Download

from .settings import User


class FtpDownload(Download):
    """
    FTP download object.
    Handles the ftp:// protocol.

    Attributes:
        user (pulpcore.download.User): User settings for authentication.
    """

    __slots__ = ('user',)

    def __init__(self, url, writer, user=None):
        """
        Args:
            url (str): A file download URL.
            writer (Writer): An object used to store downloaded file.
            user (pulpcore.download.User): User settings for authentication.
        """
        super(FtpDownload, self).__init__(url, writer)
        self.user = user or User('anonymous', 'anonymous')

    def _send(self):
        """
        Send the `RETR` (command).
        This is the *main* method responsible for implementing the actual
        download by sending a protocol specific download. The reply
        is handled by on_reply(), on_succeeded() and on_error().

        Raises:
            DownloadFailed: The download failed and could not be repaired.

        Notes:
            Must be implemented by subclass.
        """
        with FTP() as ftp:
            parsed_url = urlparse(self.url)
            ftp.connect(host=parsed_url.netloc)
            ftp.login(
                user=self.user.name,
                passwd=self.user.password)
            ftp.retrbinary(
                cmd='RETR {}'.format(parsed_url.path),
                callback=self._write,
                blocksize=self.BLOCK)

    def __str__(self):
        base = super(FtpDownload, self).__str__()
        return ' | '.join([
            base,
            str(self.user),
        ])
