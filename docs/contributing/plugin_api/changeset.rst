pulpcore.plugin.changeset
=========================

All classes documented here should be imported directly from
the ``pulpcore.plugin.changeset`` namespace.

.. automodule:: pulpcore.plugin.changeset

.. autoclass:: pulpcore.plugin.changeset.ChangeSet
    :members: apply


New Content & Artifacts
-----------------------

Classes used to define *new* content to be added to a repository.


.. autoclass:: pulpcore.plugin.changeset.RemoteContent
    :members: artifacts

.. autoclass:: pulpcore.plugin.changeset.RemoteArtifact
    :members: content


Reporting
---------

Reports and Exceptions.


.. autoclass:: pulpcore.plugin.changeset.ChangeReport
    :members:

.. autoclass:: pulpcore.plugin.changeset.ChangeFailed
    :show-inheritance:
    :members:


Additional Tools
----------------

.. autoclass:: pulpcore.plugin.changeset.BatchIterator
    :special-members: __len__, __iter__

.. autoclass:: pulpcore.plugin.changeset.SizedIterable
    :special-members: __len__
