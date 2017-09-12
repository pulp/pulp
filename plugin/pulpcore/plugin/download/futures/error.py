from gettext import gettext as _


class DownloadError(Exception):
    """
    Base for all download related exceptions.
    """
    pass


class DownloadFailed(DownloadError):
    """
    Download failed.

    Attributes:
        download (pulpcore.plugin.futures.Download): The failed download.
        reason (str): The reason it failed.
    """

    def __init__(self, download, reason=''):
        """
        Args:
            download (pulpcore.plugin.futures.Download): The failed download.
            reason (str): The reason it failed.
        """
        self.download = download
        self.reason = reason

    def __str__(self):
        return _('{r} - Failed. Reason: {d}'.format(r=self.download, d=self.reason))


class NotFound(DownloadFailed):
    """
    Resource referenced by the URL was not found.
    """
    pass


class NotAuthorized(DownloadFailed):
    """
    Not authorized to access the resource referenced by the URL.
    """
    pass
