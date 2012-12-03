Authentication
==============


Login / Logout
--------------

The default username and password are configured in ``/etc/pulp/server.conf`` in
the ``[server]`` section. By default, those values are "admin" and "admin". Below
is an example of logging in and logging out.

::

    $ pulp-admin login -u admin
    Enter password:
    Successfully logged in. Session certificate will expire at Dec  6 21:47:33 2012
    GMT.
    $ pulp-admin logout
    Session certificate successfully removed.

Users
-----


Permissions
-----------


Roles
-----


