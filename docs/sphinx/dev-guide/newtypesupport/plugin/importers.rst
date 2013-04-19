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
  Currently, the API for the base class is not published. The code can
  be found at ``Importer`` in ``platform/src/pulp/plugins/importer.py``.


Implementation
--------------

Each importer must subclass the ``pulp.plugins.importer.Importer`` class. That class defines
the operations an importer may be requested to perform on a repository. Not every method must
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

The importer implementation must implement the ``metadata`` method as
:ref:`described here <plugin_metadata>`.

Configuration Validation
^^^^^^^^^^^^^^^^^^^^^^^^

The importer implementation must implement the ``validate_config`` method as
:ref:`described here <plugin_config>`.


Functionality
-------------

There are a number of abilities an importer implementation can support. All of these are
optional; it is possible to have an importer that handles uploaded units but has no support
for synchronizing against an external repository.

The sections below will cover an overview of each feature. More information on the specifics
of how to implement them are found in the docstrings for each method.

.. warning::
 Importers that implement a sync method must also implement support for cancelling the sync.

.. _importer_sync:

Synchronize an External Respository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Methods: ``sync_repo``, ``cancel_sync_repo``

One of the most common uses of an importer is to download content from an external source
and inventory it in the Pulp server. The importer serves as an adapter between the Pulp
server and the external repository, using whatever protocols are necessary.

While the importer is responsible for downloading the unit, it is up to Pulp to determine
the absolute path on disk to store it. The importer provides a relative path for where it
would like to store the unit, taking into account enough information to create a unique
path. This is passed to the conduit's ``init_unit`` call which allows Pulp to derive the
absolute path on the server to store it. The path will be in the returned
``pulp.plugins.model.Unit`` object in the ``storage_path`` attribute.

Plugin implementations for repository sync will obviously vary wildly. Below is a short
outline of a common sync process.

#. Call the conduit's ``get_units`` method to understand what units are already associated
   with the repository being synchronized.
#. For each new unit to add to the Pulp server and associate with the repository,
   the plugin takes the following steps:

   #. Calls the conduit's ``init_unit`` which takes unit specific metadata and allows Pulp to
      populate any calculated/derived values for the unit. The result of this
      call is an object representation of the unit.
   #. Uses the ``storage_path`` field in the returned unit to save the bits for the
      unit to disk.
   #. Calls the conduit's ``save_unit`` which creates/updates Pulp's knowledge of the content
      unit and creates an association between the unit and the repository
   #. If necessary, calls the conduit's ``link_unit`` to establish any relationships between
      units.

#. For units previously associated with the repository (known from ``get_units``)
   that should no longer be, calls the conduit's ``remove_unit`` to remove that association.

.. note::
  It is valid for a unit to be purely metadata and not have a corresponding file. In these
  cases, simply specify a relative path of ``None`` to the ``init_unit`` call and ignore the
  step about using the ``storage_path``.

The conduit defines a ``set_progress`` call that should be used throughout the process
to update the Pulp server with details on what has been accomplished and what remains to be
done. The Pulp server does not require these calls. The progress message must be JSON-serializable
(primitives, lists, dictionaries) but is otherwise entirely at the discretion of the plugin writer.
The most recent progress report is saved in the database and made available to users as a means
to track the progress of the sync.

When implementing the sync functionality, the importer's ``cancel_sync_repo`` method must be
implemented as well. This call will be made on the same instance performing the sync, therefore
it is valid to use an instance variable as a flag the sync process uses to determine if it should
continue to proceed.

Upload Units
^^^^^^^^^^^^

Method: ``upload_unit``

The Pulp server provides the infrastructure for users to upload units into a repository. It is
the job of the importer to take the steps necessary to:

* Generate and save the inventoried representation of the unit.
* Determine the appropriate relative path at which to store the unit.
* Move the unit from the provided temporary location to the final storage path as provided
  by Pulp.

The conduit provides the ``init_unit`` and ``save_unit`` calls as described in :ref:`importer_sync`.
Refer to that section for more information on usage.

Import Units
^^^^^^^^^^^^

Method: ``import_units``

The Pulp server provides an API for selecting units to copy from one repository to another. The
importer's ``import_units`` method is called on the **destination repository** to handle the
copy.

There are two approaches to handling this method:

* In most cases, the unit can be shared between the two repositories. A new association is created
  between the destination repository and the original database representation of the unit. This
  approach is accomplished by simply calling the conduit's ``save_unit`` method for each unit to
  be copied.
* In certain cases, the same unit cannot be safely referenced by both repositories. A new unit
  must be created using the ``init_unit`` method and then saved to the repository with ``save_unit``
  in the same way as in :ref:`importer_sync`.

.. note::
 Take note if which attributes on the unit are required for use when importing.
 It is then possible to specify in the associate
 request's :ref:`unit association criteria <unit_association_criteria>` which fields should
 be loaded, which result in reduced RAM use during the import process,
 especially for units with a lot of metadata.

Remove Units
^^^^^^^^^^^^

Method: ``remove_units``

When a user unassociates units from a repository, the Pulp server will make the necessary database
changes to reflect the change. The ``remove_units`` method is called on the repository's importer
to allow the importer to perform any clean up steps is may need to make, such as removing any
data it may have been storing about the unit from the working directory. In most cases, this method
does not need to be overridden.

.. warning::
 This call should not remove the unit from its final location specified by Pulp. Pulp will handle
 the deletion of the file itself during its orphan clean up process.


