"""
Provides classes to support the Importer downloading.  Primarily for downloading
``metadata`` but ``may`` also be used to download content when not using the `ChangeSet`.

Examples:
    >>>
    >>> from pulpcore.plugin.download import Batch, HttpDownload
    >>>
    >>> # One file.
    >>> url = #  based on feed URL.
    >>> path = 'md'
    >>> download = HttpDownload(url, FileWriter('md.txt'))
    >>> try:
    >>>     download()
    >>> except DownloadFailed:
    >>>     # Failed
    >>> else:
    >>>     with open(path):
    >>>         # read the metadata
    >>>
    >>> # ---
    >>>
    >>> # Many files.
    >>> downloads = [
    >>>     HttpDownload(...),  # file-1
    >>>     HttpDownload(...),  # file-2
    >>>     HttpDownload(...),  # file-3
    >>> ]
    >>> with Batch(downloads) as batch:
    >>>     for plan in batch():
    >>>         try:
    >>>             plan.result()
    >>>         except DownloadFailed:
    >>>             # Failed
    >>>         else:
    >>>             # Use the downloaded file \o/
    >>> # read the metadata files.
    >>>
"""

from pulpcore.download import (  # noqa: F401
    Batch,
    BufferWriter,
    DigestValidation,
    Download,
    DownloadFailed,
    DownloadError,
    FileDownload,
    FileWriter,
    HttpDownload,
    NotAuthorized,
    NotFound,
    SizeValidation,
    SSL,
    Timeout,
    User,
    ValidationError)

from .factory import Factory  # noqa: F401
