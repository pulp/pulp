=========================
Pulp master Release Notes
=========================

Pulp master
===========

New Features
------------

* There are now two new REST APIs for :ref:`setting <set-user-metadata>` and
  :ref:`retrieving <get-user-metadata>` user supplied metadata on content units.

* There is now a new `working_directory` setting in `/etc/pulp/server.conf`. The default value is
  `/var/cache/pulp`. This is the path where `pulp_workers` process can store data while performing
  tasks. For best performance, this should be a path to local storage. This directory needs to be
  writeable by user `apache`. If running with SELinux in Enforcing mode, the path also needs to
  have `system_u:object_r:pulp_var_cache_t` security context.

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

