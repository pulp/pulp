Plugin Writer's Guide
=====================

.. note::
   This documentation is for Pulp Plugin developers. For Pulp Core development, see the
   :doc:`../../contributing/architecture/app-layout`.

Pulp Core does not manage content itself, but instead relies on plugins to add support for one
content type or another. Examples of a content type include a RPM package, Ansible role, or
Docker container.

This documentation outlines how to create a Pulp plugin that provides features like:

* Define a new content type and its attributes
* Download and save the new type of content into Pulp Core
* Publish the new type of content, allowing Pulp Core to serve it via https or http
* Export content to remote servers or CDNs
* Add custom web application views
* Implement custom features, e.g. dependency solving, retension/deletion policies, etc.

Along with this guide `an example of plugin implementation
<https://github.com/pulp/pulp_file/>`_, ``pulp_file``, is provided.
`The Plugin Template <https://github.com/pulp/plugin_template>`_ can be used to start
the plugin writing process.

.. toctree::
   :maxdepth: 2

   planning-guide
   checklist
   first-plugin
   basics
   releasing

The Pulp :doc:`../plugin-api/overview` is versioned separately from the Pulp Core and consists
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
