Plugin Writing Walkthrough
==========================

Boilerplate
-----------

Plugins are Django apps that are discoverable by the ``pulpcore`` `Django app
<plugin-django-application>` using `entry points. <plugin-entry-point>`. `pulpcore-plugin is
specified as a requirement. <https://github.com/pulp/pulp_example/blob/master/setup.py#L6>`_
Plugins use tools and parent classes that are available in the TODO(linkto, pluginapi).

Plugins are required to :ref:`implement subclasses<subclassing-platform-models>` for models,
serializers, viewsets which are :ref:`discoverable <model-serializer-viewset-discovery>`.

`A simple plugin implementation
<https://github.com/pulp/pulp_file/>`_, ``pulp_file``, is provided.

Checklist
---------

A complete Pulp plugin will do all of the following:

* Plugin django app is defined using PulpAppConfig as a parent
* Plugin entry point is defined
* pulpcore-plugin is specified as a requirement
* Necessary models/serializers/viewsets are defined and discoverable. At a minimum:
** models for plugin content type, importer, publisher
** serializers for plugin content type, importer, publisher
** viewset for plugin content type, importer, publisher
* Actions are defined:
** sync
** publish
* Errors are handled according to Pulp conventions
* Docs for plugin are available (any location and format preferred and provided by plugin writer).

Recommended Reading
-------------------

Before you get started, it is recommended that you familiarize yourself with the Pulp concepts.
TODO(link, overview). It is also encouraged to read the TODO(link, styleguide).

We provide a developer environment specifically designed for writing plugins. Please see
TODO(link, dev-setup/plugin-writer-install).

As you develop your plugin, the following documents may be especially helpful:
* TODO(link, architecture/code-layout)
* TODO(link, architecture/models)
* TODO(link, architecture/error-handling)
* TODO(link, architecutre/dependencies)
* TODO(link, glossary)
* TODO(link, bugs-features)

Plugin Template
---------------

We provide a `Plugin template <https://github.com/pulp/plugin_template>`_ that is used to generate
a bootstraped plugin. Use the `README
<https://github.com/pulp/plugin_template/blob/master/README.rst>`_ to get started. This guide
assumes that you have used the template.

The template will create a best-guess implementation of each step. It is recommended that a plugin
writer follow along and ensure that each step is correct and complete.

.. _confirm-discoverable:

Confirm Discoverability
***********************

The result of using the plugin template should already be discoverable by ``pulpcore``. To test
this,

TODO(asmacdo, does this work?)
# Start the server
# runserver --noreload
# Make an API call TODO(link, httpie)
http http://pulp3.dev:8000/api/v3/status/

If your plugin is discoverable, it will be listed in the respoonse.


.. _define-content-type:

Define your plugin Content type
*******************************


To define a new content type(s), e.g. ``ExampleContent``:

* :class:`pulpcore.plugin.models.Content` should be subclassed and extended with additional
  attributes to the plugin needs,
* define ``TYPE`` class attribute which is used for filtering purposes,
* uniqueness should be specified in ``Meta`` class of newly defined ``ExampleContent`` model,
* ``unique_together`` should be specified for the ``Meta`` class of ``ExampleContent`` model,
* create a serializer for your new Content type as a subclass of
  :class:`pulpcore.plugin.serializers.ContentSerializer`,
* create a viewset for your new Content type as a subclass of
  :class:`pulpcore.plugin.viewsets.ContentViewSet`

:class:`~pulpcore.plugin.models.Content` model should not be used directly anywhere in plugin code.
Only plugin-defined Content classes are expected to be used.

To make sure all of this is working, you should have a new API endpoint available

  $ http http://pulp3.dev:8000/content/example/

# TODO(asmacdo) update to pulp_file
Check ``pulp_example`` implementation of `the ExampleContent
<https://github.com/pulp/pulp_example/blob/master/pulp_example/app/models.py#L87-L114>`_ and its
`serializer <https://github.com/pulp/pulp_example/blob/master/pulp_example/app/serializers.py#L7-L13>`_
and `viewset <https://github.com/pulp/pulp_example/blob/master/pulp_example/app/viewsets.py#L13-L17>`_.
For a general reference for serializers and viewsets, check `DRF documentation
<http://www.django-rest-framework.org/api-guide/viewsets/>`_.


.. _define-importer:

Define your plugin Importer
---------------------------

To define a new importer, e.g. ``ExampleImporter``:

* :class:`pulpcore.plugin.models.Importer` should be subclassed and extended with additional
  attributes to the plugin needs,
* define ``TYPE`` class attribute which is used for filtering purposes,
* create a serializer for your new importer as a subclass of
  :class:`pulpcore.plugin.serializers.ImporterSerializer`,
* create a viewset for your new importer as a subclass of
  :class:`pulpcore.plugin.viewsets.ImporterViewSet`.

:class:`~pulpcore.plugin.models.Importer` model should not be used directly anywhere in plugin
code, except as the parent class to the plugin importer. Only plugin-defined Importer classes are
expected to be used.

There are several important aspects relevant to importer implementation which were briefly mentioned
# TODO(asmacdo) where is this now?
in the :ref:`understanding-models` section:

.. _define-sync-:

Define your sync task
---------------------
# TODO(asmacdo)
* ``sync`` method should be defined on a plugin importer model ``ExampleImporter``,

Plugin Responsibilities for Synchronization:

* Download and analyze repository metadata from a remote source.
* Decide what needs to be added to repository or removed from it.
** For each item that needs to be added:
*** Create an instance of ``ExampleContent``
*** Create an instance (or instances if necessary) of :class:`~pulpcore.plugin.models.Artifact`
*** Use PendingArtifact and PendingContent to update the database.
** Get each ContentUnit to remove from the database.

Sync should use the following tools to interact with ``pulpcore``:
* pulpcore.plugin.tasking.WorkingDirectory to write to the file system
* pulpcore.plugin.facades.RepositoryVersion to safely create a new RepositoryVersion TODO(link,
  plugin-api/RepositoryVersion)
* :class:`~pulpcore.plugin.changeset.ChangeSet` to `add/remove content to a RepositoryVersions <changeset-docs>`
* :class:`~pulpcore.plugin.models.ProgressBar` to report the progress. TODO(link,
  pluginapi/progress bar


.. _define-publisher:

Define your plugin Publisher
----------------------------

To define a new publisher, e.g. ``ExamplePublisher``:

* :class:`pulpcore.plugin.models.Publisher` should be subclassed and extended with additional
  attributes to the plugin needs,
* define ``TYPE`` class attribute which is used for filtering purposes,
* create a serializer for your new publisher a subclass of
  :class:`pulpcore.plugin.serializers.PublisherSerializer`,
* create a viewset for your new publisher as a subclass of
  :class:`pulpcore.plugin.viewsets.PublisherViewSet`.

:class:`~pulpcore.plugin.models.Publisher` model should not be used directly anywhere in plugin
code. Only plugin-defined Publisher classes are expected to be used.

# TODO(asmacdo) change to pulp_file
Check ``pulp_example`` implementation of `the ExamplePublisher
<https://github.com/pulp/pulp_example/blob/master/pulp_example/app/models.py#L117-L181>`_.

.. _define-publish-task:

Define your publish task
------------------------
# TODO(asmacdo)
One of the ways to perform publishing:

* Find :class:`~pulpcore.plugin.models.ContentArtifact` objects which should be published
* For each of them create and save instance of :class:`~pulpcore.plugin.models.PublishedArtifact`
  which refers to :class:`~pulpcore.plugin.models.ContentArtifact` and
  :class:`~pulpcore.app.models.Publication` to which this artifact belongs.
* Generate and write to a disk repository metadata
* For each of the metadata objects create and save  instance of
  :class:`~pulpcore.plugin.models.PublishedMetadata` which refers to a corresponding file and
  :class:`~pulpcore.app.models.Publication` to which this metadata belongs.
* Use :class:`~pulpcore.plugin.models.ProgressBar` to report progress of some steps if needed.

