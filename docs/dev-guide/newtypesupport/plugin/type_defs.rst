Type Definitions
================

Overview
--------

A type definition is used to configure Pulp to support inventorying a type
of content unit, such as an RPM or a Puppet module. Pulp uses the data in the
definition to configure the database storage for those units with uniqueness
constraints and to optimize queries relevant to that type.


Attributes
----------

Each type definition contains the following attributes.

``id``
  Programmatic identifier for the content type. The ID must be unique across
  all type definitions installed on the Pulp server.

``display_name``
  User-friendly name of the type.

``description``
  User-friendly description of the type.

``unit_key``
  List of all attributes that will be in units of this type that, when combined,
  represent the unique key for a unit. Pulp will enforce the
  uniqueness for units of this type based on this attribute.

``search_indexes``
  List of added non-unique indexes to add for storing units of the type. Each
  entry in the list may itself be another list to represent a compound index.

``referenced_types``
  List of type IDs for other types that are related to the type being defined.
  This nature of relationship is not explicitly defined; depending on the types
  of units involved it may be parent/child, dependent units, or something else.
  Pulp uses this information when the importer indicates to link a unit with
  another.

The ``unit_key`` attribute creates one or more indexes in the database as well.
Given a value of ["a", "b", "c"], the following indexes are automatically
created and need not be specified in the ``search_indexes`` field:

 * a
 * a, b
 * a, b, c

Note that neither an index on just "b" nor the index "b, c" are automatically
created.


Format
------

Type definitions are defined in a JSON file. Multiple types may be defined in
a single file. The file must be placed in the ``/usr/lib/pulp/plugins/types``
directory and has no restrictions on its name.


Installation
------------

Once the type definition file is in the appropriate directory, the
``pulp-manage-db`` script must be run to install the type. This script should
also be run after making any changes to the type definition.


Sample
------

Below is a sample type definition file, taken from the Puppet support bundle.

::

 {"types": [
     {
         "id" : "puppet_module",
         "display_name" : "Puppet Module",
         "description" : "Puppet Module",
         "unit_key" : ["name", "version", "author"],
         "search_indexes" : ["author", "tag_list"]
     }
 ]}

This file installs a single type that is referenced by the id
"puppet_module". Each inventoried module will have a unique tuple of name,
version, and author in its metadata. In addition to the indexes created by
the unit key, indexes will be created on the "author" and "tag_list" attributes
in each unit.
