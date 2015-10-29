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


Deprecation
-----------

Supported Platforms Changes
---------------------------

* If run on CentOS or Red Hat Enterprise Linux, the Pulp server now requires either
  version 7.1+ or 6.7+.

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

Rest API Changes
----------------

* Tasks with complete states (except `canceled` state) can now be deleted.

Binding API Changes
-------------------

Plugin API Changes
------------------

