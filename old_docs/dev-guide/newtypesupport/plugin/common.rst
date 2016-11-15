Plugin Conventions
==================

.. _plugin_config:

Configuration
-------------

Validation
^^^^^^^^^^

It is up to the plugin writer to determine what configuration values are necessary for the
plugin to function.

Pulp performs no validation on the configuration for a plugin. The ``validate_config``
method in each plugin subclass is used to verify the user-entered values for a repository.
This is called when the plugin is first added to the repository and on all subsequent
configuration changes. The configuration is sent to the Pulp server as a JSON document through its
REST APIs and will be deserialized before being passed to the plugin.

This call must ensure the configuration to be used when running the plugin will be valid
for the repository. If this call indicates an invalid configuration, the plugin will
not be added to the repository (for the add call) or the configuration changes
will not be saved to the database (for the update configuration call).

The docstring for the method describes the format of the returned value.

Format
^^^^^^

Each call into a plugin passes the configuration the call should use for its execution.
The configuration is contained in a ``pulp.plugins.config.PluginCallConfiguration`` instance.
This object is a wrapper on top of the three different locations a configuration value
can come from:

* **Overrides** - Most calls allow the user to specify configuration values as a parameter
  when they are invoked. These values are made available to the plugin for the operation's
  execution, however they are not saved in the server.
* **Repository-level** - When an importer or distributor is attached to a repository, the
  Pulp server saves the configuration for that plugin with the repository. These
  values are only used for operations on that repository. For
  example, if an importer is configured to synchronize from an external feed, the URL
  of that feed would be stored on a per repository basis.
* **Plugin-level** - Each importer and distributor may be paired with a static
  configuration file on disk. These are JSON files that are loaded by the Pulp server when
  the plugins are initialized. Configuration values in this location are available to all
  instances of the importer/distributor.

The ``PluginCallConfiguration`` defines a method called ``get(str)`` that will retrieve
the value for the given key. This call will check the three configuration locations in the
order listed above. The first value found for the key is returned, removing the need for
the plugin writer to apply this prioritization on their own.


.. _plugin_lifecycle:

Life Cycle Methods
------------------

Both types of plugins define a number of methods related to the lifecycle of the plugin on
a particular repository. These methods are called when the importer/distributor is added to
or removed from a repository. Examples include ``importer_added(repo, config`` and
``distributor_removed(repo, config)``.

In many cases, these methods can be ignored. The default implementation will not raise an
error. Their usage is typically to perform any initialization in the plugin's
:ref:`working directory <working_directories>` that is necessary before the first plugin
operation is invoked.


.. _plugin_metadata:

Metadata Method
---------------

Both types of plugins require a metadata method to be overridden from the base class. The
``metadata()`` method is responsible for providing Pulp with information on how the
plugin works. The following information must be returned from the metadata call. The docstring
for the method describes the format of the returned value.

* **ID** - Unique ID that is used to refer to this type of plugin. This must be unique
  for all plugins installed in the Pulp server.
* **Display Name** - User-friendly description of what the plugin does.
* **Supported Types** - List of IDs for all content types that may be handled by the plugin.
  If there is no type definition found for any of the IDs referenced here, the server will
  fail to start.


.. _conduits:

Conduits
--------

A :term:`conduit` is an object passed to a plugin when an method is executed. The conduit is used
to access functionality in the Pulp server itself. Each method is given a custom conduit type
depending on the needs of the method being invoked. Consult the docstrings for each method in
the plugin base class for more information on the conduit class that will be used.

.. warning::
  Plugins should not retain any state between calls. Conduits are typically scoped to the
  repository being used; reusing old conduit instances can lead to data corruption.


.. _scratchpads:

Scratchpads
-----------

A :term:`scratchpad` is used to store information across multiple operations run by the plugin.
Each importer and distributor on a repository is given its own scratchpad. A plugin may
only edit its own scratchpad for the repository being acted on.

The scratchpad is retrieved through the conduit's ``get_scratchpad()`` method and
updated with ``set_scratchpad(object)``. The scratchpad is stored in the database,
therefore its value must be able to be pickled. It is recommended to use either a single
string or a dictionary of string pairs.

Additionally, there exists a scratchpad at the repository level, accessible to *all* importers
and distributors on the repository. This can be used to share information between different
plugins. It is highly recommended to avoid using this wherever possible so as to not tightly
couple plugins together. The repository scratchpad can be accessed using ``get_repo_scratchpad()``
and ``set_repo_scratchpad(object)`` and carries the same pickle restriction as described above.


.. _working_directories:

Working Directories
-------------------

Each plugin on a repository is given a unique location on disk. This directory should be used
for storing any temporary files that need to be created when the plugin is used. These directories
are automatically deleted when the repository is deleted. The location of the working directory
can be found in the repository instance (``pulp.plugins.model.Repository``) passed into each
plugin call.


.. _plugin_installation:

Installation
------------

There are two ways to install a plugin.

.. _plugin_entry_points:

Entry Points
^^^^^^^^^^^^

The plugin may define a method that will serve as its entry point. The method must accept zero
arguments and return a tuple of the following:

* Class of the plugin itself. This must be a subclass of either ``pulp.plugins.importer.Importer``
  or ``pulp.plugins.distributor.Distributor``.
* Plugin-level configuration to use for that plugin. See :ref:`plugin_config` for more information
  on the scope of these configuration values.

A sample is as follows:

::

  def entry_point():
      return DemoImporter, {}

  class DemoImporter(Importer):
      ...


Python entry points are advertised within the package's ``setup.py`` file. Multiple entry points
may be advertised by the same setup file. A sample from the Puppet plugins is below:

::

  from setuptools import setup, find_packages

  setup(
      name='pulp_puppet_plugins',
      version='2.0.0',
      license='GPLv2+',
      packages=find_packages(exclude=['test', 'test.*']),
      author='Pulp Team',
      author_email='pulp-list@redhat.com',
      entry_points = {
          'pulp.distributors': [
              'distributor = pulp_puppet.plugins.distributors.distributor:entry_point',
          ],
          'pulp.importers': [
              'importer = pulp_puppet.plugins.importers.importer:entry_point',
          ],
      }
  )


.. _plugin_directory:

Directory Loading
^^^^^^^^^^^^^^^^^

For one-off testing purposes, the code for a plugin can be placed directly
in a specific directory without the need to install to site-packages. The entry
point method described above is the preferred way to integrate new plugins:

* Create directory in ``/usr/lib/pulp/plugins/`` under the appropriate plugin type.
* Add ``__init__.py`` to created directory.
* Add ``importer.py`` or ``distributor.py`` as appropriate.
* In the above module, add the classes that subclass ``Importer`` or ``Distributor`` as appropriate.

Additionally, for directory loaded plugins, Pulp will automatically load any configuration files
found in the plugin's directory. The configuration within will be made available to each
call as described in :ref:`plugin_config`. The only restriction on the name of the configuration
file is that it end with ``.conf`` and be placed in the directory created in the first step
above.
