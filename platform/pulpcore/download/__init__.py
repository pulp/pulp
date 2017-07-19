"""
This package provides objects used for downloading files.
The workhorse is the ``Download`` object which performs the task of downloading a single file.
A more natural name for this class might be a download `Task` but this might cause confusion
with celery tasks in Pulp.  Here, a `download` is used as a noun and has a command-object
design pattern.  That is, the download is callable.  The Batch provides a way to perform multiple
downloads concurrently.

The model::

                     |*-------1 Batch
            Download |--------------------------------------------------|
               ^     |1-----------------* Validation *-----------------1| Writer
               |                               ^                            ^
        -------|------                         |                            |
        |      |      |             ---------------------           -----------------
        |      |      |             |                    |          |               |
  HttpDownload |  FtpDownload  SizeValidation  DigestValidation  FileWriter    BufferWriter
               |
         FileDownload

Recipes:

    A single download.

    >>>
    >>> download = HttpDownload('http://my-url', FileWriter('put-file-here'))
    >>> download()
    >>> # Go use the file.
    >>>

    Multiple downloads concurrently.

    >>>
    >>> downloads = [
    >>>     HttpDownload('http://my-url0', FileWriter('put-file-here0')),
    >>>     FileDownload('file://my-url1', FileWriter('put-file-here1')),
    >>>     FtpDownload('ftp://my-url2', FileWriter('put-file-here2')),
    >>> ]
    >>>
    >>> with Batch(downloads) as batch:
    >>>     for plan in batch():
    >>>         try:
    >>>             plan.result()
    >>>         except Exception:
    >>>             # Failed
    >>>         else:
    >>>             # Use the downloaded file \o/
    >>>

    Download a text file to a use as a string.

    >>>
    >>> download = HttpDownload('http://my-url', BufferWriter())
    >>> download()
    >>> document = download.writer.read()
    >>> # Use the document
    >>>

"""

from .batch import Batch  # noqa
from .error import DownloadError, DownloadFailed, NotFound, NotAuthorized  # noqa
from .event import Event  # noqa
from .ftp import FtpDownload  # noqa
from .file import FileDownload  # noqa
from .http import HttpDownload  # noqa
from .settings import Settings, SSL, Timeout, User  # noqa
from .single import Download  # noqa
from .validation import ValidationError, SizeValidation, DigestValidation  # noqa
from .writer import Writer, FileWriter, BufferWriter  # noqa
