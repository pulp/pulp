=========================
Pulp master Release Notes
=========================

Pulp master
===========

New Features
------------

* Multiple instances of ``pulp_celerybeat`` can now run simultaneously.
  If one of them goes down, another instance will dispatch scheduled tasks as usual.

* Pulp now supports lazy content loading. As part of this support a new package,
  ``pulp-streamer``, is now available.

* When downloading content, Pulp now uses the system certificate authority trust
  store rather than the certificate authority trust store bundled with
  ``python-requests``.

* Content applicability for an updated repository is calculated in parallel.

Deprecation
-----------

Dependency/Platform Changes
---------------------------

* If run on CentOS or Red Hat Enterprise Linux, the Pulp server now requires either
  version 7.1+ or 6.7+.
* pymongo >= 3.0.0 is now required.

Client Changes
--------------

* Tasks with complete states (except `canceled` state) can now be deleted. This can be done
  using `pulp-admin tasks purge` command.

Agent Changes
-------------

Bugs
----

Known Issues
------------


Upgrade Instructions for 2.7.x --> master
-----------------------------------------

Upgrade the packages using::

    sudo yum update

After yum completes you should migrate the database using::

    sudo -u apache pulp-manage-db

.. note::
    If using systemd, you need to reload the systemd process before restarting services. This can
    be done using::

        sudo systemctl daemon-reload

After migrating the database, restart `httpd`, `pulp_workers`, `pulp_celerybeat`, and
`pulp_resource_manager`.

Upgrade From Older Release
--------------------------

If you are upgrading from pulp older than 2.4.0, you must first upgrade to some release between
2.4.0 and 2.7.x, and then upgrade to 2.8.0 or greater.

Rest API Changes
----------------

* Tasks with complete states (except `canceled` state) can now be deleted.

* The API for regenerating content applicability for updated repositories no longer returns a
  :ref:`call_report`. Instead a :ref:`group_call_report` is returned.

Binding API Changes
-------------------

Plugin API Changes
------------------

