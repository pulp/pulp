pulpcore.plugin.download.futures
================================

All classes documented here should be imported directly from
the ``pulpcore.plugin.download.futures`` namespace.

.. automodule:: pulpcore.plugin.download.futures



Single File
-----------


.. autoclass:: pulpcore.plugin.download.futures.HttpDownload
    :members:
    :special-members: __call__

.. autoclass:: pulpcore.plugin.download.futures.FileDownload
    :members:
    :special-members: __call__


Multiple Files (concurrent)
---------------------------


.. autoclass:: pulpcore.plugin.download.futures.Batch
    :members: download, shutdown
    :special-members: __call__


File Validation
---------------

.. autoclass:: pulpcore.plugin.download.futures.SizeValidation
    :members:

.. autoclass:: pulpcore.plugin.download.futures.DigestValidation
    :members:
    :special-members: __call__


Writers
-------

Downloading consists of two related operations.  First, is reading the file content
from a remote source.  Second, is writing those bits locally.  The most typical case is
to write the bits to a file on the local filesystem and is accomplished using
a `FileWriter`.  Another case, is to store the file content (text) in memory and then
inspect as a `str`.  As a convenience, this may be done using the `BufferWriter`.


.. autoclass:: pulpcore.plugin.download.futures.FileWriter
    :members:

.. autoclass:: pulpcore.plugin.download.futures.BufferWriter
    :members:


Settings
--------

.. autoclass:: pulpcore.download.SSL
    :members:

.. autoclass:: pulpcore.download.User
    :members:

.. autoclass:: pulpcore.download.Timeout
    :members:


Errors
------

A download is successful unless an exception is raised.

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
