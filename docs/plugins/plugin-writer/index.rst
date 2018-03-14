.. _plugin-writer-guide:

Plugin Writer's Guide
=====================

Flow
Plugin writers should begin with a
Overview
plugins
plugin-writer-guide
plugin template quickstart
plugin-api
contributing/architecture
rest api
bugs/features


Plugin Responsibilities
------------------------

TODO(combine with what plugins do)
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

# TODO(asmacdo) use file plugin instead
Along with this guide `an example of plugin implementation
<https://github.com/pulp/pulp_example/>`_, ``pulp_example``, is provided.

.. toctree::
   :maxdepth: 2

   basics
   planning-guide
   walkthrough
   releasing
   cli
   planning-guide

The Pulp :doc:`../plugin-api/overview` is versioned separately from the Pulp Core and consists
of everything importable within the :mod:`pulpcore.plugin` namespace. When writing plugins, care should
be taken to only import Pulp Core components exposed in this namespace; importing from elsewhere
within the Pulp Core (e.g. importing directly from ``pulpcore.app``, ``pulpcore.exceptions``, etc.)
is unsupported, and not protected by the Pulp Plugin API's semantic versioning guarantees.

.. warning::

    # TODO(asmacdo) Revise this
    Exactly what is versioned in the Plugin API, and how, still has yet to be determined.
    This documentation will be updated to clearly identify what guarantees come with the
    semantic versioning of the Plugin API in the future. As our initial plugins are under
    development prior to the release of Pulp 3.0, the Plugin API can be assumed to have
    semantic major version 0, indicating it is unstable and still being developed.

.. Pulp models
.. ===========
..
.. Understanding models
.. --------------------
.. # TODO(asmacdo) move models of this to contributor docs
.. # TODO(asmacdo) update for RepositoryVersions
.. # TODO(asmacdo) update from language guide
..
.. There are models which are expected to be used in plugin implementation, so understanding what they
.. are designed for is useful for a plugin writer. Each model below has a link to its documentation
.. where its purpose, all attributes and relations are listed.
..
.. Here is a gist of how models are related to each other and what each model is responsible for.
..
..   :class:`~pulpcore.plugin.models.RepositoryContent` is used to represent this relation.
.. * :class:`~pulpcore.plugin.models.Content` can have :class:`~pulpcore.plugin.models.Artifact`
..   associated with it. :class:`~pulpcore.plugin.models.ContentArtifact` is used to represent this
..   relation.
.. * :class:`~pulpcore.plugin.models.ContentArtifact` can have
..   :class:`~pulpcore.plugin.models.RemoteArtifact` associated with it.
.. * :class:`~pulpcore.plugin.models.Artifact` is a file.
.. * :class:`~pulpcore.plugin.models.RemoteArtifact` contains information about
..   :class:`~pulpcore.plugin.models.Artifact` from a remote source, including URL to perform
..   download later at any point.
.. * :class:`~pulpcore.plugin.models.Importer` knows specifics of the plugin
..   :class:`~pulpcore.plugin.models.Content` to put it into Pulp.
..   :class:`~pulpcore.plugin.models.Importer` defines how to synchronize remote content. Pulp
..   Platform provides support for concurrent  :ref:`downloading <download-docs>` of remote content.
..   Plugin writer is encouraged to use one of them but is not required to.
.. * :class:`~pulpcore.plugin.models.PublishedArtifact` refers to
..   :class:`~pulpcore.plugin.models.ContentArtifact` which is published and belongs to a certain
..   :class:`~pulpcore.app.models.Publication`.
.. * :class:`~pulpcore.plugin.models.PublishedMetadata` is a repository metadata which is published,
..   located in ``/var/lib/pulp/published`` and belongs to a certain
..   :class:`~pulpcore.app.models.Publication`.
.. * :class:`~pulpcore.plugin.models.Publisher` knows specifics of the plugin
..   :class:`~pulpcore.plugin.models.Content` to make it available outside of Pulp.
..   :class:`~pulpcore.plugin.models.Publisher` defines how to publish content available in Pulp.
.. * :class:`~pulpcore.app.models.Publication` is a result of publish operation of a specific
..   :class:`~pulpcore.plugin.models.Publisher`.
.. * :class:`~pulpcore.app.models.Distribution` defines how a publication is distributed for a specific
..   :class:`~pulpcore.plugin.models.Publisher`.
.. * :class:`~pulpcore.plugin.models.ProgressBar` is used to report progress of the task.
..
..
.. An important feature of the current design is deduplication of
.. :class:`~pulpcore.plugin.models.Content` and :class:`~pulpcore.plugin.models.Artifact` data.
.. :class:`~pulpcore.plugin.models.Content` is shared between :class:`~pulpcore.app.models.Repository`,
.. :class:`~pulpcore.plugin.models.Artifact` is shared between
.. :class:`~pulpcore.plugin.models.Content`.
.. See more details on how it affects importer implementation in :ref:`define-importer` section.
.. TODO:
..     After a concept is fully explained, link to related Workflows


