"""
Download tools.
"""
from .event import Fetched
from .validation import DigestValidation


class MetricsCollector:
    """
    Download metrics collector.

    The set of metrics collected include:
     - Total number of bytes downloaded.
     - Standard set of file digests.

    Attributes:
        algorithms (dict): Dictionary of validations keyed by algorithm.
            Used only to leverage digest calculation.
        size (int): The total file size in bytes.

    Examples:
        >>> download = ...
        >>> metrics = MetricsCollector(download)
        >>> download()
        >>> metrics.dict()
            {'size': 1109, 'sha1': aFc12, 'sha256': '837e9ab1', ...}
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
        self.algorithms = {
            n: DigestValidation.find_algorithm(n) for n in DigestValidation.ALGORITHMS
        }
        self.size = 0
        if download:
            self.attach(download)

    def attach(self, download):
        """
        Args:
            download (pulpcore.download.Download): A download object
                for which metrics are collected.
        """
        download.register(Fetched.NAME, self.fetched)

    def dict(self):
        """
        Get a dictionary representation of the collected metrics.

        Returns:
            dict: Collected metrics.
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
        return str(self.dict())
