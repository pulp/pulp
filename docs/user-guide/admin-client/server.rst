Inspecting the Server
=====================


Pulp as a Platform
------------------

The Pulp server has very little built in functionality. To provide the
functionality that administrators rely on, Pulp loads a number of plugins that
define ``types`` and ``importers`` and ``distributors``. The former are
definitions of categories of content units and the metadata that needs to be
associated with them. The latter two are classes of plugins that allow Pulp to
manage content units, of particular types, by bring them into the server and
making them available from the server respectively.

This page shows how to query the server for each of these classes of plugins.


Content Unit Types
------------------

The **pulp-admin** command line client provides the ``server`` section and the
``types`` command to query the server about the content unit type definitions
that have been loaded.

::

 $ pulp-admin server types
 +----------------------------------------------------------------------+
                         Supported Content Types
 +----------------------------------------------------------------------+

 Id:               distribution
 Display Name:     Distribution
 Description:      Kickstart trees and all accompanying files
 Referenced Types:
 Search Indexes:   id, family, variant, version, arch
 Unit Key:         id, family, variant, version, arch

 [snip]

 Id:               rpm
 Display Name:     RPM
 Description:      RPM
 Referenced Types: erratum
 Search Indexes:   name, epoch, version, release, arch, filename, checksum,
                   checksumtype
 Unit Key:         name, epoch, version, release, arch, checksumtype, checksum

 [snip]

 Id:               puppet_module
 Display Name:     Puppet Module
 Description:      Puppet Module
 Referenced Types:
 Search Indexes:   author, tag_list
 Unit Key:         name, version, author


The output above shows a snippet of the types that are defined by the default
plugins that have been developed with the Pulp server. Each type has the
following fields:

 * **Id**: this is a programmatic id that the server uses to identify the type
 * **Display Name**: an optional, human-friendly, display name
 * **Description**: an optional description of the type
 * **Referenced Types**: a list of other types that may be referenced by a content unit of this type in some way
 * **Search Indexes**: metadata fields that can potentially be used as search criteria
 * **Unit Key**: a metadata field, or set of fields, that will uniquely identify a content unit of this type


Content Unit Importers
----------------------

The **pulp-admin** command line client provides the ``server`` section and the
``importers`` command to query the server about the importer plugins that have
been loaded.

::

 $ pulp-admin server importers
 +----------------------------------------------------------------------+
                           Supported Importers
 +----------------------------------------------------------------------+

 Id:           puppet_importer
 Display Name: Puppet Importer
 Types:        puppet_module

 Id:           yum_importer
 Display Name: Yum Importer
 Types:        distribution, drpm, erratum, package_group, package_category, rpm,
               srpm


The output above shows the importers that have been developed along side the
Pulp platform. Each importer has the following fields:

 * **Id**: a programmatic id that the server uses to identify the importer
 * **Display Name**: an optional, human-friendly, display name
 * **Types**: a list of type ids that the importer can handle



Content Unit Distributors
-------------------------

The **pulp-admin** command line client provides the ``server`` section and the
``distributors`` command to query the server about the distributor plugins that
have been loaded.

::

 $ pulp-admin server distributors
 +----------------------------------------------------------------------+
                          Supported Distributors
 +----------------------------------------------------------------------+

 Id:           yum_distributor
 Display Name: Yum Distributor
 Types:        rpm, srpm, drpm, erratum, distribution, package_category,
               package_group

 Id:           export_distributor
 Display Name: Export Distributor
 Types:        rpm, srpm, drpm, erratum, distribution, package_category,
               package_group

 Id:           puppet_distributor
 Display Name: Puppet Distributor
 Types:        puppet_module


The output above shows the distributors that have been developed along side the
Pulp platform. Each distributor has the following fields:

 * **Id**: a programmatic id that the server uses to identify the distributor
 * **Display Name**: an optional, human-friendly, display name
 * **Types**: a list of type ids that the distributor can handle

