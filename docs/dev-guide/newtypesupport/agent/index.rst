Agent Handlers
==============

Overview
--------

The Pulp agent processes messages sent from the server to a consumer. These
messages include informing the consumer of a new binding to a repository or
a request to install one or more content units.

The implementation for how those requests are found will vary depending on the
types of units involved. The agent supports writing :term:`handlers <handler>`
that will be used depending on the data in the operation. For example, when
a bind request is received for a yum repository, a specific handler is invoked
to edit the appropriate repository definition file.

An example extension can be found on the :doc:`example` page.


Documentation
-------------

.. toctree::
   :maxdepth: 2

   handlers
   example

