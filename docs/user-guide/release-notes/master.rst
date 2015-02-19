=========================
Pulp master Release Notes
=========================

Pulp master
===========

New Features
------------

* There are now two new REST APIs for :ref:`setting <set-user-metadata>` and
  :ref:`retrieving <get-user-metadata>` user supplied metadata on content units.
* After running pulp-manage-db during this upgrade, database indexes for all the different content
  types will no longer be dropped as part of pulp-manage-db. As a result, users will no longer have
  to worry about custom indexes disappearing during database migrations.

Deprecation
-----------

Client Changes
--------------

Agent Changes
-------------

Bugs
----

Known Issues
------------

.. _2.6.x_upgrade_to_master:

Upgrade Instructions for 2.6.x --> master
-----------------------------------------

Rest API Changes
----------------

Binding API Changes
-------------------

Plugin API Changes
------------------

