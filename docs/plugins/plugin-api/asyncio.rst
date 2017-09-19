.. _asyncio-docs:

pulpcore.plugin.download.asyncio
================================

The module implements downloaders that solve many of the common problems plugin writers have while
downloading remote data. A high level list of features provided by these downloaders include:

* auto-configuration from importer settings (auth, ssl, proxy)
* efficient parallel downloading
* digest and size validation computed during download
* grouping downloads together to return to the user when all files are downloaded
* customizable download behaviors via subclassing

All classes documented here should be imported directly from the
``pulpcore.plugin.download.asyncio`` namespace.


Overview
--------

For basic synchronous or parallel downloading of files, the easiest usage is using the
:ref:`DownloaderFactory <downloader-factory>` and scheduling those downloads with asyncio.

For parallel downloading where multiple files need to be downloaded before a content unit can be
saved, use the :ref:`GroupDownloader <group-downloader>`. The `GroupDownloader` manages the asyncio
loop for you, which some users may prefer even for basic usage.

.. _downloader-factory:

Basic Downloading
-----------------

The DownloaderFactory constructs a downloader for any given url. It contains built-in support for
`http://`, `https://` and `file://`. It creates :ref:`HttpDownloader <http-downloader>` objects for
`http` and `https` and :ref:`FileDownloader <file-downloader>` objects for `file`. All downloaders
are auto-configured from the core settings saved on an importer.

All downloaders can be run in parallel using asyncio. Each downloader has a `run()` method which
returns a coroutine object that asyncio can run.

:ref:`HttpDownloader <http-downloader>` objects produced by an instantiated DownloaderFactory share
a session, which contains a connection pool inside, connection reusage and keep-alives.

Size and/or digest based validation can be configured using arguments provided to the
:func:`~pulpcore.plugin.download.asyncio.DownloaderFactory.build`. method.

.. autoclass:: pulpcore.plugin.download.asyncio.DownloaderFactory
    :members:

.. _download-result:

Download Results
----------------

The download result contains all the information about a completed download and is returned from a
the downloader's `run()` method when the download is complete.

.. autoclass:: pulpcore.plugin.download.asyncio.DownloadResult
    :no-members:

.. _group-downloader:

Downloading Groups of Files
---------------------------

Motivation
##########

A content unit that requires multiple files to be all downloaded before the content unit can be
saved is a common problem. Consider a content unit `foo`, that requires three files, A, B, and C.
One option is to use the :ref:`DownloaderFactory <downloader-factory>` to generate a downloader for
each URL (A, B, C) and wait for those downloads to complete before saving the content unit `foo` and
its associated :class:`~pulpcore.plugin.models.Artifact` objects. The issue with this approach is
that you also want to download other content units, e.g. a unit named `bar` with files (D, E, and F)
and while waiting on A, B, and C you are not also downloading D, E, and F in parallel.

GroupDownloader Overview
########################

The GroupDownloader allows you to schedule a :class:`~pulpcore.plugin.download.asyncio.Group`
of downloads in a way that results are returned when the entire Group is ready instead of
download-by-download. This is significant because multiple downloads from multiple groups still run
in parallel. See the examples below.

.. autoclass:: pulpcore.plugin.download.asyncio.GroupDownloader
    :members:

.. autoclass:: pulpcore.plugin.download.asyncio.Group
    :members:

.. _exception-handling:

Exception Handling
------------------

All downloaders are expected to handle recoverable errors automatically. When an unrecoverable error
occurs it can be one of two types of errors, i.e. one of the
:ref:`validation exceptions <validation-exceptions>`, or a protocol specific error. A validation
error example would be if a download size is expected to be 1945 bytes but it is actually 1990
bytes, a :class:`~pulpcore.plugin.download.asyncio.SizeValidationError` would be raised. An example
of a protocol specific error would be an HTTP 403 response.

In both cases these are fatal exceptions and should likely be recorded with the
:meth:`~pulpcore.plugin.tasking.Task.append_non_fatal_error` interface. A fatal exception on a single
download likely does not cause an entire sync to fail, so a downloader's fatal exception is recorded
as a non-fatal exception on the task. Plugin writers can also opt to halt the entire task by
allowing the exception be uncaught and propogate up.

.. _http-downloader:

HttpDownloader
--------------

This downloader is an asyncio-aware parallel downloader which is the default downloader produced by
the :ref:`downloader-factory` and the :ref:`group-downloader` For urls starting with `http://` or
`https://`.

.. autoclass:: pulpcore.plugin.download.asyncio.HttpDownloader
    :members:

.. _file-downloader:

FileDownloader
--------------

This downloader is an asyncio-aware parallel file reader which is the default downloader produced by
the :ref:`downloader-factory` and the :ref:`group-downloader` for urls starting with file://

.. autoclass:: pulpcore.plugin.download.asyncio.FileDownloader
    :members:

.. _base-downloader:

BaseDownloader
--------------

This is an abstract downloader that is meant for subclassing. All downloaders are expected to be
descendants of BaseDownloader.

.. autoclass:: pulpcore.plugin.download.asyncio.BaseDownloader
    :members:

.. autoclass:: pulpcore.plugin.download.asyncio.attach_url_to_exception
    :members:

.. _validation-exceptions:

Validation Exceptions
---------------------

.. autoclass:: pulpcore.plugin.download.asyncio.DigestValidationError
.. autoclass:: pulpcore.plugin.download.asyncio.SizeValidationError
.. autoclass:: pulpcore.plugin.download.asyncio.DownloaderValidationError
