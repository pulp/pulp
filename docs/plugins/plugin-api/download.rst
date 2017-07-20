pulpcore.plugin.download
========================

All classes documented here should be imported directly from
the ``pulpcore.plugin.download`` namespace.

.. automodule:: pulpcore.plugin.download



Single File
-----------


.. autoclass:: pulpcore.plugin.download.HttpDownload
    :members:
    :special-members: __call__

.. autoclass:: pulpcore.plugin.download.FileDownload
    :members:
    :special-members: __call__


Multiple Files (concurrent)
---------------------------


.. autoclass:: pulpcore.plugin.download.Batch
    :members: download, shutdown
    :special-members: __call__


File Validation
---------------

.. autoclass:: pulpcore.plugin.download.SizeValidation
    :members:

.. autoclass:: pulpcore.plugin.download.DigestValidation
    :members:
    :special-members: __call__


Writers
-------

Downloading consists of two related operations.  First, is reading the file content
from a remote source.  Second, is writing those bits locally.  The most typical case is
to write the bits to a file on the local filesystem and is accomplished using
a `FileWriter`.  Another case, is to store the file content (text) in memory and then
inspect as a `str`.  As a convenience, this may be done using the `BufferWriter`.


.. autoclass:: pulpcore.plugin.download.FileWriter
    :members:

.. autoclass:: pulpcore.plugin.download.BufferWriter
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

.. autoclass:: pulpcore.plugin.download.DownloadError
    :show-inheritance:
    :members: download, reason

.. autoclass:: pulpcore.plugin.download.DownloadFailed
    :show-inheritance:
    :members: download, reason

.. autoclass:: pulpcore.plugin.download.NotAuthorized
    :show-inheritance:
    :members: download, reason

.. autoclass:: pulpcore.plugin.download.NotFound
    :show-inheritance:
    :members: download, reason

.. autoclass:: pulpcore.plugin.download.ValidationError
    :show-inheritance:
    :members: download, reason
