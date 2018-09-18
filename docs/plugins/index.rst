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
     - `Yes <https://pypi.org/project/pulp-file/>`__
     - No

   * - Ansible plug-in
     - `Ansible plug-in docs <https://github.com/pulp/pulp_ansible/blob/master/README.rst>`_
     - `Ansible plug-in source <https://github.com/pulp/pulp_ansible>`_
     - `Ansible plug-in tracker <https://pulp.plan.io/projects/ansible_plugin?jump=welcome>`_
     - `Yes <https://pypi.org/project/pulp-ansible/>`__
     - No

   * - Python plug-in
     - `Python plug-in docs <http://pulp-python.readthedocs.io/en/latest/>`_
     - `Python plug-in source <https://github.com/pulp/pulp_python/tree/3.0-dev>`_
     - `Python plug-in tracker <https://pulp.plan.io/projects/pulp_python?jump=welcome>`_
     - `Yes <https://pypi.org/project/pulp-python/>`__
     - No

   * - | Chef cookbook
       | plug-in
     - `Cookbook plug-in docs <https://github.com/gmbnomis/pulp_cookbook/blob/master/README.rst>`_
     - `Cookbook plug-in source <https://github.com/gmbnomis/pulp_cookbook>`_
     - `Cookbook plug-in tracker <https://github.com/gmbnomis/pulp_cookbook/issues>`_
     - `Yes <https://pypi.org/project/pulp-cookbook/>`__
     - No

.. note::
   Are we missing a plugin? Let us know via the pulp-dev@redhat.com mailing list.

Plugin Writer's Guide
---------------------
.. toctree::
   plugin-writer/index
   plugin-api/overview
