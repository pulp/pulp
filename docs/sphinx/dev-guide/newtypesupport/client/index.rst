Client Extensions
======================

Overview
--------

Both the Pulp Admin Client and the Pulp Consumer Client use an extension
mechanism to allow additions and changes to be made depending on a developer's
needs. For the plugin writer, these additions typically center around specific
functionality for the types being supported by the plugin. For example, the
configuration values for an :term:`importer` are likely unique for each type
of importer. Extensions are used to provide an interface catered to that
specific configuration.


Documentation
-------------

.. toctree::
   :maxdepth: 2

   extensions
   example

