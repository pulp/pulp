from ftplib import FTP
from urllib.parse import urlparse

from .single import Download


class FtpDownload(Download):
    """
    FTP download object.
    """

    def _send(self):
        """
        Send the RETR command.
        """
        with FTP() as ftp:
            parsed_url = urlparse(self.url)
            ftp.connect(host=parsed_url.netloc)
            ftp.login(user=self.user, passwd=self.password)
            ftp.retrbinary(
                cmd='RETR {}'.format(parsed_url.path),
                callback=self._write,
                blocksize=self.BLOCK)
