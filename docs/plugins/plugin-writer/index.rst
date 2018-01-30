.. _plugin-writer-guide:

Plugin Writer's Guide
=====================

Plugin Respoonsibilities
------------------------

Each plugin must do each of the following:

Define a content type:
   Each plugin must implement subclasses of ContentUnit, ContentUnitSerializer,
   and ContentUnitViewset.

Add user-facing import settings:
   Each plugin is responsible for adding any settings that are required to pull content from an
   external source. They do this by implementing subclasses of Importer, ImporterSerializer, and
   ImporterViewset. The ImporterViewset must also add "action" endpoints that deploy celery tasks
   to interact with external sources.

Add user-facing publish settings:
   Each plugin is responsible for adding any settings that are required to publish content. They do
   this by implementing subclasses of Publisher, PublisherSerializer, and PublisherViewset.

Add sync task(s):
   Any code that makes changes to the ContentUnit set in a Repository must create a new
   RepositoryVersion in a celery task that is executed asynchronously.

Add publish tasks(s):
   TODO(asmacdo)
   Plugins define celery tasks that create Publications, generating metadata and andContentUnit set

Available Plugins
-----------------

A<<<<<<< HEAD
A=======

.. note::
   This documentation is for Pulp Plugin developers. For Pulp Core development, see the
   TODO(asmacdo, fixlink):doc`../../contributing/3.0-development/app-layout`.

The Pulp Core does not manage content itself, but instead relies on plugins to add support for one
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
<https://github.com/pulp/pulp_example/>`_, ``pulp_example``, is provided.
`The Plugin Template <https://github.com/pulp/plugin_template>`_ can be used to start
the plugin writing process.
>>>>>>> f90c29ed46d74b7aa019eb794364ccd1f1a260fe

.. toctree::
   :maxdepth: 2

   walkthrough
   concepts
   releasing
   cli
   planning-guide
   releasing
   cli

The Pulp :doc:`../plugin-api/overview` is versioned separately from the Pulp Core and consists
of everything importable within the :mod:`pulpcore.plugin` namespace. When writing plugins, care should
be taken to only import Pulp Core components exposed in this namespace; importing from elsewhere
within the Pulp Core (e.g. importing directly from ``pulpcore.app``, ``pulpcore.exceptions``, etc.)
is unsupported, and not protected by the Pulp Plugin API's semantic versioning guarantees.

>>>>>>> f90c29ed46d74b7aa019eb794364ccd1f1a260fe
.. warning::

    # TODO(asmacdo) Revise this
    Exactly what is versioned in the Plugin API, and how, still has yet to be determined.
    This documentation will be updated to clearly identify what guarantees come with the
    semantic versioning of the Plugin API in the future. As our initial plugins are under
    development prior to the release of Pulp 3.0, the Plugin API can be assumed to have
    semantic major version 0, indicating it is unstable and still being developed.
