Importers
=========

Overview
--------

The fundamental role of an importer is to bring new units into a Pulp repository. The typical
method is the sync process through which the contents of an external source (yum repository,
Puppet Forge, etc.) are downloaded and inventoried on the Pulp server. Additionally, the importer
is also responsible for handling uploaded units (inventorying and persistence on disk) and
any logic involved with copying units between repositories.

Operations cannot be performed on an importer until it is attached to a repository. When adding
an importer to a repository, the importer's configuration will be stored in the Pulp server
and provided to the importer in each operation. More information on how this configuration
functions can be found in the :ref:`configuration section <plugin_config>` of this guide.

Only one importer may be attached to a repository at a time.

The :doc:`common` page describes behavior and APIs common to both importers and distributors.

.. note::
  Currently, the API for the client context is not published. The code can
  be found at ``Importer`` in ``platform/src/pulp/plugins/importer.py``.


Implementation
--------------

Each importer must subclass the ``pulp.plugins.importer.Importer`` class. That class defines
the operations an importer may be requested to perform on a repository. Not ever method must
be overridden in the subclass. Some, such as the :ref:`lifecycle methods <plugin_lifecycle>`
will have no effect. Others, such as ``upload_unit``, will raise an exception indicating the
operation is not supported by the importer if not overridden.

.. warning::
  The importer instance is not reused between invocations. Any state maintained in the importer
  is only valid during the current operation's execution. If state is required across multiple
  operations, the :ref:`plugin's scratchpad <scratchpads>` should be used to store the necessary
  information.

There are two methods in the ``Importer`` class that must be overridden in order for the
importer to work:

Metadata
^^^^^^^^

The ``metadata`` method is responsible for providing Pulp with information on how the
plugin works. The following information must be returned from the metadata call. The docstring
for the method describes the format of the returned value.

 * **ID** - Unique ID that is used to refer to this type of importer. This must be unique
   for all importers installed in the Pulp server.
 * **Display Name** - User-friendly description of what the does.
 * **Supported Types** - List of IDs for all content types that may be handled by the importer.
   If there is no type definition found for any of the IDs referenced here, the server will
   fail to start.

Configuration Validation
^^^^^^^^^^^^^^^^^^^^^^^^

The ``validate_config`` method is used to verify the user-entered values for a repository.
This is called when the importer is first added to the repository and on all subsequent
configuration changes.

This call must ensure the configuration to be used when running the importer will be valid
for the repository. If this call indicates an invalid configuration, the importer will
not be added to the repository (for the add importer call) or the configuration changes
will not be saved to the database for an update call (for the update configuration call).

The docstring for the method describes the format of the returned value.

.. note::
  The configuration is specified to this call in a ``PluginCallConfiguration`` instance
  as described in the :ref:`plugin_config` section. However, there will never be
  an override configuration in this object; this call's purpose is to validate the
  repository-level and plugin-level configurations.
