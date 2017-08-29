import hashlib

from pulpcore.app.models import Artifact
from pulpcore.download import Event


class DownloadMonitor:
    """
    Monitor a download and collect information:
     - Total number of bytes downloaded.
     - Standard set of file digests.

    Attributes:
        algorithms (dict): Dictionary of validations keyed by algorithm.
            Used only to leverage digest calculation.
        size (int): The total bytes downloaded.  When the download
            has completed successfully, this is the total size of the
            file in bytes.

    Examples:
        >>> download = ...
        >>> monitor = DownloadMonitor(download)
        >>> download()
        >>> monitor.facts()
            {'size': 1109, 'sha1': 'aFc12', 'sha256': '837e9ab1', ...}
    """

    __slots__ = (
        'algorithms',
        'size'
    )

    def __init__(self, download=None):
        """
        Args:
            download (pulpcore.download.Download): An (optional) download object
                for which metrics are collected.
        """
        self.algorithms = {n: hashlib.new(n) for n in Artifact.DIGEST_FIELDS}
        self.size = 0
        if download:
            self.attach(download)

    def attach(self, download):
        """
        Args:
            download (pulpcore.download.Download): A download object
                for which metrics are collected.
        """
        download.register(Event.FETCHED, self.fetched)

    def facts(self):
        """
        Get a dictionary representation of the collected information.
        The facts include the `size` and calculated digests as defined
        by Artifact.DIGEST_FIELDS.

        Returns:
            dict: Collected facts.
        """
        metrics = {n: a.hexdigest() for n, a in self.algorithms.items()}
        metrics['size'] = self.size
        return metrics

    def update(self, buffer):
        """
        Update metrics using the fetched buffer.

        Args:
            buffer (bytes): A buffer of downloaded data.
        """
        self.size += len(buffer)
        for algorithm in self.algorithms.values():
            algorithm.update(buffer)

    def fetched(self, event):
        """
        The FETCHED event handler.

        Args:
            event (pulpcore.download.Fetched): A buffer fetched event.
        """
        self.update(event.buffer)

    def __str__(self):
        return str(self.facts())
