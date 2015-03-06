=========================
Pulp master Release Notes
=========================

Pulp master
===========

New Features
------------

* There are now two new REST APIs for :ref:`setting <set-user-metadata>` and
  :ref:`retrieving <get-user-metadata>` user supplied metadata on content units.

* `unit_<type>` collection indices will be destroyed and recreated for the last time when
  pulp-manage-db runs during upgrade. All subsequent executions of pulp-manage-db will only create
  new indices based on unit type definitions. Any user created indices for `unit_<type>`
  collections will persist between upgrades.

* There is now a new `working_directory` setting in `/etc/pulp/server.conf`. The default value is
  `/var/cache/pulp`. This is the path where `pulp_workers` process can store data while performing
  tasks. For best performance, this should be a path to local storage. This directory needs to be
  writeable by user `apache`. If running with SELinux in Enforcing mode, the path also needs to
  have `system_u:object_r:pulp_var_cache_t` security context.

Deprecation
-----------

Client Changes
--------------

* Admin and consumer Pulp clients now support -v and -vv flags to get additional
  information in case of failures. Exceptions raised for CLI and API level
  failures are not logged to the log files anymore. Instead, you can get the details
  of the failures on STDERR stream by using verbose flag. You can look at an example
  of the usage of verbose flag in the
  :ref:`admin client troubleshooting section <client-verbose-flag>`.

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

