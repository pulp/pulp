Releasing Your Plugin
=====================

.. warning::

    All the content below is here due to refactor of initial 3.0 docs
    and should be revisited for correctness. 

Packaging
---------

The Plugin API is available from PyPI as pulpcore-plugin. A plugin writer needs to specify the
minimum version of pulpcore-plugin their plugin is dependent on. A plugin writer does not need to
specify which version of pulpcore would work with their plugin since pulpcore-plugin will
resolve the pulpcore dependency. Please see :doc:`release notes <../../release_notes/index>`
for the supported versions of pulpcore.

