Authentication
==============

This guide covers basic authentication and authorization in the Pulp Platform.

Basic Authentication of Users
-----------------------------

All pulp-admin commands accept username and password to capture authentication credentials.

::

    $ pulp-admin --help
    Usage: pulp-admin [options]

    Options:
      -h, --help            show this help message and exit
      -u USERNAME, --username=USERNAME
                            username for the Pulp server; if used will bypass the
                            stored certificate and override a username specified
                            in ~/.pulp/admin.conf
      -p PASSWORD, --password=PASSWORD
                            password for the Pulp server; must be used with
                            --username. If used will bypass the stored certificate
                            and override a password specified in ~/.pulp/admin.conf
      --debug               enables debug logging
      --config=CONFIG       absolute path to the configuration file
      --map                 prints a map of the CLI sections and commands


Pulp Admin client allows the user to specify username and password credentials
in the user's local admin.conf ``~/.pulp/admin.conf``. Using the conf file 
avoids having to pass user credentials repeatedly using the command line.
Also reading the password from a file that can only be read by certain users 
is more secure because it cannot be shown by listing the system processes.

::

    # Add the following snippet to ``~/.pulp/admin.conf``

    [auth]
    username: admin
    password: admin

    # This enables the user to run pulp-admin commands without providing a username
    # and password using the command line

    $ pulp-admin repo list
    +----------------------------------------------------------------------+
                                  Repositories
    +----------------------------------------------------------------------+


pulp-admin searches for a username and password to use in the following order:
    - credentials specified from the command line.
    - credentials set in the user's ``~/.pulp/admin.conf``.

Pulp Server installation comes with one default user created with admin level privileges.
Username and password for this user can be configured in ``/etc/pulp/server.conf`` at the time
of installation.

Below is an example of basic authentication of users based on their username and password when
running a pulp-admin command.

::

    $ pulp-admin repo list
    Enter password:
    +----------------------------------------------------------------------+
                                  Repositories
    +----------------------------------------------------------------------+


Note that username and password are parameters to the ``pulp-admin`` command, not the sub-command,
like ``repo list`` in this case. You can also pass the password parameter on the command line
with ``--password`` argument, but this is not a recommended method. Users should use interactive password
as a preferred method.

Rather than specifying the credentials on each call to pulp-admin, a user can log in to the Pulp server.
Logging in stores a user credentials certificate at ``~/.pulp/user-cert.pem``.

::

    $ pulp-admin login -u admin
    Enter password:
    Successfully logged in. Session certificate will expire at Dec  6 21:47:33 2012
    GMT.

Subsequent commands to pulp-admin will no longer require the username-password arguments
and will instead use the user certificate. The user can be logged out by using
the ``pulp-admin logout`` command.

::

    $ pulp-admin logout
    Session certificate successfully removed.


Layout of Auth Section
----------------------

The root level ``auth`` section contains sub-sections to create and manage
Pulp users, roles and their permissions for various resources.

::

    $ pulp-admin auth
    Usage: pulp-admin auth [SUB_SECTION, ..] COMMAND
    Description: user, role and permission commands

    Available Sections:
    permission - manage granting, revoking and listing permissions for resources
    role       - manage user roles
    user       - manage users

Users
-----

Users can be created to perform various administrative tasks on the Pulp Server. You can
configure them with either admin level access or limited access to a few resources
on the server.

::

	$ pulp-admin auth user --help
	Usage: pulp-admin user [SUB_SECTION, ..] COMMAND
	Description: manage users

	Available Commands:
	create - creates a user
  	delete - deletes a user
  	list   - lists summary of users registered to the Pulp server
  	search - search items while optionally specifying sort, limit, skip, and requested fields
  	update - changes metadata of an existing user

Here is an example of creating and updating a user:

::

	$ pulp-admin auth user create --login test-user
	Enter password for user [test-user] :
	Re-enter password for user [test-user]:
	User [test-user] successfully created

If you intend to update the password for a user, you can use ``-p`` flag as shown in the example
below to be prompted for a new password.

::

	$ pulp-admin auth user update --login test-user --name "Test User" -p
	Enter new password for user [test-user] :
	Re-enter new password for user [test-user]:
	User [test-user] successfully updated

You can also pass it on the command line with ``--password`` argument, but this method is just to provide
a simpler way for scripting and is not recommended. Users should use interactive password update
as a preferred method.

The ``user list`` command lists a summary of all users. It also accepts arguments to list
all the details or specific fields for users.

::

	$ pulp-admin auth user list --details
	+----------------------------------------------------------------------+
        	                         Users
	+----------------------------------------------------------------------+

	Login:  admin
	Name:   admin
	Roles:  super-users


	Login:  test-user
	Name:   test-user
	Roles:

::

    $ pulp-admin auth user list --fields roles
    +----------------------------------------------------------------------+
    	                             Users
    +----------------------------------------------------------------------+

    Login:  admin
    Roles:  super-users


    Login:  test-user
    Roles:


Users can be removed from the Pulp server using the ``user delete`` command.

::

	$ pulp-admin auth user delete --login test-user
	User [test-user] successfully deleted

Users belonging to the ``super-users`` role can be deleted as well, as long as there is at least one such user
remaining in the system.

::

	$ pulp-admin auth user delete --login admin
	The server indicated one or more values were incorrect. The server provided the
	following error message:

   	The last superuser [admin] cannot be deleted

	More information can be found in the client log file ~/.pulp/admin.log.

Permissions
-----------

Permissions to various resources can be accessed or manipulated using ``pulp-admin auth permission``
commands. There are 5 types of permissions - CREATE, READ, UPDATE, DELETE and EXECUTE. Permissions are
granted and revoked from a resource which is essentially a REST API path.

Here are a few examples of accessing and manipulation permissions:

::

	$ pulp-admin auth permission list --resource /
	+----------------------------------------------------------------------+
		                       Permissions for /
	+----------------------------------------------------------------------+

	Admin:  CREATE, READ, UPDATE, DELETE, EXECUTE


The following command will give permissions to create, read and update repositories to ``test-user``.

::

	$ pulp-admin auth permission grant --resource /v2/repositories/ --login test-user -o create -o update -o read
	Permissions [/v2/repositories/ : ['CREATE', 'UPDATE', 'READ']] successfully granted
	to user [test-user]

::

	$ pulp-admin auth permission list --resource /v2/repositories/
	+----------------------------------------------------------------------+
    	                 Permissions for /repositories
	+----------------------------------------------------------------------+

	Test-user:  CREATE, UPDATE, READ

The following command will revoke permissions to create and update repositories from ``test-user``.

::

	$ pulp-admin auth permission revoke --resource /v2/repositories/ --login test-user -o create -o update
	Permissions [/v2/repositories/ : ['CREATE', 'UPDATE']] successfully revoked from
	user [test-user]

.. note::
    The ``/v2`` prefix and the trailing ``/`` are always present in a resource name for permission commands.

Roles
-----

In order to efficiently administer permissions, Pulp uses the notion of roles to enable an administrator
to grant and revoke permission on a resource to a group of users instead of individually. The ``pulp-admin auth role``
command provides the ability to list the currently defined roles, create/delete roles, and manage user membership
in a role. Pulp installation comes with a default ``super-users`` role with admin level privileges, and the default
admin user belongs to this role.

The ``role list`` command is used to list the current roles.

::

	$ pulp-admin auth role list
	+----------------------------------------------------------------------+
	                             	Roles
	+----------------------------------------------------------------------+

	Id:     super-users
	Users:  admin

A role can be created and deleted by specifying a role id.

::

	$ pulp-admin auth role create --role-id consumer-admin
	Role [consumer-admin] successfully created

	$ pulp-admin auth role delete --role-id consumer-admin
	Role [consumer-admin] successfully deleted

A user can be added and removed from a role using ``role user add`` and ``role user remove`` commands respectively.
Note that both the user and the role should exist on the pulp server.

::

    $ pulp-admin auth role user add --role-id super-users --login test-user
    User [test-user] successfully added to role [super-users]

    $ pulp-admin auth role user remove --role-id super-users --login test-user
    User [test-user] successfully removed from role [super-users]

Permissions can be granted and revoked from roles just like users. In this case all the users belonging to the given
role will inherit these permissions.

::

    $ pulp-admin auth permission grant --resource /repositories --role-id test-role -o read
    Permissions [/repositories : ['READ']] successfully granted to role [test-role]

    $ pulp-admin auth permission revoke --resource /repositories --role-id test-role -o read
    Permissions [/repositories : ['READ']] successfully revoked from role [test-role]


