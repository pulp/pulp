.. _plugin-api:

Plugin API
==========

The Pulp Plugin API is versioned separately from Pulp Core. It is governed by `semantic
versioning <http://semver.org/>`_. Backwards incompatible changes may be made until the
Plugin API reaches stability with v1.0. For the latest version of the Plugin API see
:doc:`release notes <../../release_notes/index>`.

The Pulp :doc`../plugin-api/index` is versioned separately from the Pulp Core and consists
of everything importable within the :mod:`pulpcore.plugin` namespace. When writing plugins, care should
be taken to only import Pulp Core components exposed in this namespace; importing from elsewhere
within the Pulp Core (e.g. importing directly from ``pulpcore.app``, ``pulpcore.exceptions``, etc.)
is unsupported, and not protected by the Pulp Plugin API's semantic versioning guarantees.



.. toctree::
    models
    serializers
    storage
    viewsets
    tasking
    download
    changeset

.. automodule:: pulpcore.plugin
    :imported-members:
