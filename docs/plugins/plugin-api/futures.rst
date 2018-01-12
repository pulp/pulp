.. _futures-docs:

pulpcore.plugin.download.futures
================================

All classes documented here should be imported directly from
the ``pulpcore.plugin.download.futures`` namespace.

.. automodule:: pulpcore.plugin.download.futures



Basic Downloading
-----------------

.. autoclass:: pulpcore.plugin.download.futures.Download
    :members:
    :special-members: __call__

Support `http://` and `https://` URLs.

.. autoclass:: pulpcore.plugin.download.futures.HttpDownload
    :members:
    :special-members: __call__

Support `file:///` URLs.


.. autoclass:: pulpcore.plugin.download.futures.FileDownload
    :members:
    :special-members: __call__


Multiple Files (concurrent)
---------------------------

The `Batch` is provided to support multiple concurrent execution of downloads.

.. autoclass:: pulpcore.plugin.download.futures.Batch
    :members: download, shutdown
    :special-members: __call__


File Validation
---------------

Downloaded files may be validated by associating one or more validation objects
to the `Download`.  All validations are updated with each buffer downloaded.  After
the download has completed, all validations are applied.  A failed validation raises
`ValidationError`.  Custom validation may be created by subclassing the `Validation`
base class.

.. autoclass:: pulpcore.plugin.download.futures.Validation
    :members:

.. autoclass:: pulpcore.plugin.download.futures.SizeValidation
    :members:

.. autoclass:: pulpcore.plugin.download.futures.DigestValidation
    :members:
    :special-members: __call__

Events
------

During the download flow, predefined events are raised.  This provides an opportunity for external
objects to participate in the download flow without having to subclass the download object.
This is intended to support common customizations such as:

 * Progress reporting.
 * Error handling.
 * Digest calculation.
 * Auth handshaking such as *auth tokens*.
 * Header manipulation.

.. autoclass:: pulpcore.plugin.download.futures.event.Event
    :members:

.. autoclass:: pulpcore.plugin.download.futures.event.Prepared
    :members:

.. autoclass:: pulpcore.plugin.download.futures.event.Sent
    :members:

.. autoclass:: pulpcore.plugin.download.futures.event.Replied
    :members:

.. autoclass:: pulpcore.plugin.download.futures.event.Succeeded
    :members:

.. autoclass:: pulpcore.plugin.download.futures.event.Failed
    :members:

.. autoclass:: pulpcore.plugin.download.futures.event.Error
    :members:

.. autoclass:: pulpcore.plugin.download.futures.event.Fetched
    :members:


Writers
-------

Downloading consists of two related operations.  First, is reading the file content
from a remote source.  Second, is writing those bits locally.  The most typical case is
to write the bits to a file on the local filesystem and is accomplished using
a `FileWriter`.  Another case, is to store the file content (text) in memory and then
inspect as a `str`.  As a convenience, this may be done using the `BufferWriter`.

.. autoclass:: pulpcore.plugin.download.futures.Writer
    :members:

.. autoclass:: pulpcore.plugin.download.futures.FileWriter
    :members:

.. autoclass:: pulpcore.plugin.download.futures.BufferWriter
    :members:


Settings
--------

Common settings are abstracted to provide consistency across download objects.

.. autoclass:: pulpcore.plugin.download.futures.SSL
    :members:

.. autoclass:: pulpcore.plugin.download.futures.User
    :members:

.. autoclass:: pulpcore.plugin.download.futures.Timeout
    :members:


Errors
------

A download is successful unless an exception is raised.  All subclasses of `Download` are
expected to handle non-fatal and recoverable exceptions.  Anticipated exceptions that are
fatal and non-recoverable will be caught and raised as `DownloadError`.  Unanticipated
exceptions indicating that something is broken will be raised *as-is*.

.. autoclass:: pulpcore.plugin.download.futures.DownloadError
    :show-inheritance:
    :members: download, reason

.. autoclass:: pulpcore.plugin.download.futures.DownloadFailed
    :show-inheritance:
    :members: download, reason

.. autoclass:: pulpcore.plugin.download.futures.NotAuthorized
    :show-inheritance:
    :members: download, reason

.. autoclass:: pulpcore.plugin.download.futures.NotFound
    :show-inheritance:
    :members: download, reason

.. autoclass:: pulpcore.plugin.download.futures.ValidationError
    :show-inheritance:
    :members: download, reason


Shared Resources
----------------

Resources such as connection pools and authentication tokens may be shared through collaboration.
Each `Download` has a reference to an individual or shared *thread-safe* context that may be used
to share resources.

.. autoclass:: pulpcore.plugin.download.futures.context.Context
    :members:

.. autoclass:: pulpcore.plugin.download.futures.context.Cache
    :members:


Factory
-------

A factory is provided to build download objects based on URL and configured
with standard `Importer` attributes.

.. autoclass:: pulpcore.plugin.download.futures.Factory
    :members:
