=========================
Pulp master Release Notes
=========================

Pulp master
===========

New Features
------------


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

Binding API Changes
-------------------

Plugin API Changes
------------------

