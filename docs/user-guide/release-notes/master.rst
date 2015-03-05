=========================
Pulp master Release Notes
=========================

Pulp master
===========

New Features
------------

* There are now two new REST APIs for :ref:`setting <set-user-metadata>` and
  :ref:`retrieving <get-user-metadata>` user supplied metadata on content units.

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

