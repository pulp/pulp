Plugins
=======

Plugins add support for a type of content to Pulp. For example, the
`file_plugin <https://github.com/pulp/pulp_file>`_ adds support for Pulp to manage files.

All known Pulp plugins are listed below. If you are interested in creating a plugin, see
:doc:`these docs <plugin-writer/index>`.

And don't hesitate to :ref:`contact us<community>` with any questions during development.
Let us know when the plugin is ready and we will be happy to add it to the list of available plugins for Pulp!


.. _plugin-table:

Plugin List
-----------

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

.. toctree::
   plugin-writer/index
   plugin-api/overview
