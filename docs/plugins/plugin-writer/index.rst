Plugin Writer's Guide
=====================

This documentation is for Pulp Plugin developers. For Core development,
see the :doc:`../../contributing/3.0-development/app-layout`.

The Pulp Core does not manage any content itself. This functionality is provided by
its plugins, which use the Pulp Core Plugin API to manage specific types of content,
like RPM Packages or Puppet Modules. To do this, the Pulp Core extends the Django
Web Framework and the Django REST Framework to provide a set of base classes that can be
implemented in plugins to manage content in a way that is consistent across plugins, while
still allowing plugin writers the freedom to define their workflows as they deem necessary.

Along with this guide `an example of plugin implementation
<https://github.com/pulp/pulp_example/>`_, ``pulp_example``, is provided.
`The Plugin Template <https://github.com/pulp/plugin_template>`_ can be used to start
the plugin writing process.

.. toctree::
   :maxdepth: 2
   
   checklist
   first-plugin
   basics
   releasing
   cli

The Pulp :doc:`../plugin-api/index` is versioned separately from the Pulp Core and consists
of everything importable within the :mod:`pulpcore.plugin` namespace. When writing plugins, care should
be taken to only import Pulp Core components exposed in this namespace; importing from elsewhere
within the Pulp Core (e.g. importing directly from ``pulpcore.app``, ``pulpcore.exceptions``, etc.)
is unsupported, and not protected by the Pulp Plugin API's semantic versioning guarantees.

.. warning::

    Exactly what is versioned in the Plugin API, and how, still has yet to be determined.
    This documentation will be updated to clearly identify what guarantees come with the
    semantic versioning of the Plugin API in the future. As our initial plugins are under
    development prior to the release of Pulp 3.0, the Plugin API can be assumed to have
    semantic major version 0, indicating it is unstable and still being developed.
