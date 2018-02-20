Plugins
=======

Plugins add support for a type of content to Pulp. Pulp needs at least one plugin to manage
content. For example, `file_plugin <https://github.com/pulp/pulp_file>`_ adds support for Pulp to
manage files.

All known Pulp plugins are listed below. If you are interested in creating a plugin, see
:doc:`these docs <plugin-writer/index>`.

.. toctree::

   plugin-api/overview
   plugin-writer/index


What plugins do
---------------

   At a minimum:

   * models for plugin content type, importer, publisher
   * serializers for plugin content type, importer, publisher
   * viewsets for plugin content type, importer, publisher
   * tasks for sync, publish

 * :ref:`Errors are handled according to Pulp conventions <error-handling-basics>`
 * Docs for plugin are available (any location and format preferred and provided by plugin writer)

Available Plugins
-----------------

All known Pulp plugins are listed below.
If you are interested in writing your own plugin, those docs will help you:
And don't hesitate to :doc:`contact us<../bugs-features>` with any questions before and during development.
Let us know when the plugin is ready and we will be happy to add it to the list of available plugins for Pulp!


.. list-table::
   :header-rows: 1
   :widths: auto
   :align: center

   * - Pulp Plugin
     - Docs
     - Source
     - Tracker
     - Install with PyPI
     - Install with RPM

   * - File
     - `File plug-in docs <https://github.com/pulp/pulp_file/blob/master/README.rst>`_
     - `File plug-in source <https://github.com/pulp/pulp_file>`_
     - `File plug-in tracker <https://pulp.plan.io/projects/pulp_file?jump=welcome>`_
     - Yes
     - No

.. note::
   Are we missing a plugin? Let us know via the pulp-dev@redhat.com mailing list.

