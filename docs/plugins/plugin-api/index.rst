Plugin API
==========

The Pulp Plugin API is versioned separately from Pulp Core. It is governed by `semantic
versioning <http://semver.org/>`_. Backwards incompatible changes may be made until the
Plugin API reaches stability with v1.0. For the latest version of the Plugin API see
:doc:`release notes <../../release_notes/index>`.


.. toctree::
    models
    serializers
    viewsets
    changeset
    futures

.. automodule:: pulpcore.plugin
    :imported-members:

.. automodule:: pulpcore.plugin.cataloger

.. automodule:: pulpcore.plugin.profiler

.. automodule:: pulpcore.plugin.tasking
