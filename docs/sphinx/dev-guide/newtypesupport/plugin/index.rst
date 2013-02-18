Server Plugins
==============

Introduction
------------

There are three components that can be used in a server side plugin:

 * *Type definitions* are used to tell Pulp about the types of content that
   will be stored. These definitions contain metadata about the type itself
   (e.g. name, description) and clues about the structure of the unit, such
   as uniqueness information and search indexes. Pulp uses that information to
   properly configure its internal storage of the unit to be optimized for
   the expected usage of the type. Type definitions are defined in a JSON
   document.
 * *Importers* are used to handle the addition of content to a repository. This
   includes both synchronizing content from an external source or handling
   user-uploaded content units. An importer is linked to one or more type
   definitions to describe the types of units it will handle. At runtime,
   an importer is attached to a repository to provide the behavior of that
   repository's sync call. Importers are Python code that is run by the server.
 * *Distributors* are added to a repository to publish its content. The
   definition of publish varies depending on the distributor and can include
   anything from serving the repository's content over HTTP to generating an
   RSS feed with information about the repositories contents. One or more
   distributors may be attached to a repository, allowing the repository to
   be exposed over a number of different mechanisms. Like importers,
   distributors are Python code executed on the server.


Documentation
-------------

Details on each server-side component can be found in the pages below:

.. toctree::
   :maxdepth: 2

   type_defs
   migrations
   importers
   distributors
   common
   example

