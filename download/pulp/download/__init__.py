"""
This package provides objects used for downloading files.
The workhorse is the `Download` object which performs the task of downloading a single file.
A more natural name for this class might be a download `Task` but this might cause confusion
with celery tasks in Pulp.  Here, a `download` is used as a noun and has a command-object
design pattern.  That is, the download is callable.  The Batch provides a way to perform multiple
downloads concurrently.

The model:

          Download *-------1 Batch
              ^
              |
       ---------------
       ^              ^
       |              |
  HttpDownload  FtpDownload

Recipes:

    A single download.

    >>>
    >>> download = HttpDownload('http://my-url', path='put-file-here')
    >>> download()
    >>> # Go use the file.
    >>>

    Multiple downloads concurrently.

    >>>
    >>> downloads = [
    >>>     HttpDownload('http://my-url0', path='put-file-here0'),
    >>>     HttpDownload('http://my-url1', path='put-file-here1'),
    >>>     FtpDownload('ftp://my-url2', path='put-file-here2'),
    >>> ]
    >>>
    >>> with Batch(downloads) as batch:
    >>>     for plan in batch():
    >>>         if plan.succeeded:
    >>>             # Go use the file.
    >>>         else:
    >>>             # Be sad.
    >>>

    Download a text file to a use as a string.

    >>>
    >>> download = HttpDownload('http://my-url')  # no path
    >>> download()
    >>> document = str(download.writer)
    >>> # Use the document
    >>>

"""

from .batch import Batch
from .ftp import FtpDownload
from .http import HttpDownload
from .single import Download, DownloadFailed
from .validation import ValidationError, SizeValidation, DigestValidation
from .writer import Writer, FileWriter, TextWriter
