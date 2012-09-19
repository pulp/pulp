Pulp Client Extensions
======================

Overview
--------

Both the Pulp Admin Client and the Pulp Consumer Client use an extension mechanism
to allow additions and changes to be made to depending on a developer's needs.

Getting Started
---------------

Quick start guide to writing an extension:

* Create directory in ``/var/lib/pulp/client/*/extensions/``.
* Add ``__init__.py`` to created directory.
* Add ``pulp_cli.py`` or ``pulp_shell.py`` as appropriate.
* In the above module, add a ``def initialize(context)`` method.
* The ``context`` object (see :doc:`ClientContext API documentation <context-api>` contains the CLI or shell instance that can be manipulated to add the extension's functionality.

API Documentation
-----------------

.. toctree::
   :maxdepth: 2

   context-api
   pulpprompt-api
   pulpcli-api

