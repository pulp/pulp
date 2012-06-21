Installation
============

Prerequisites
-------------

* On RHEL 5, Pulp does not currently work with SELinux. SELinux must be
  set to Permissive or Disabled.
* The following ports must be open into the server:

 * 80 for consumers to access repositories served over HTTP
 * 443 for consumers to access repositories served over HTTPS
 * 443 for clients (both admin and consumer) to access Pulp APIs
 * 5672 for consumers to connect to the message bus if it is left unsecured
 * 5674 for consumers to connect to the message bus if it is running over HTTPS

* The following ports must be open into consumer systems:

 * 5672 to connect to the message bus if it is left unsecured
 * 5674 to connect to the message bus if it is running over HTTPS

* The mod_python Apache module must be uninstalled or not loaded. Pulp uses
  mod_wsgi which conflicts with mod_python and will cause the server to fail.

Installation
------------

General
^^^^^^^

1. Download the appropriate repo definition file from the Pulp repository:

 * Fedora: http://repos.fedorapeople.org/repos/pulp/pulp/fedora-pulp.repo
 * RHEL: http://repos.fedorapeople.org/repos/pulp/pulp/rhel-pulp.repo

.. note::
  Currently, the only enabled repository in these files is the v1 production
  repository. These instructions apply to the v2 codebase. As such, be sure
  to disable the v1 repositories and enable one of the v2 repository definitions
  in the above files.


2. For RHEL systems, the EPEL repositories are required. More information can
   be found at: `<http://fedoraproject.org/wiki/EPEL/FAQ#howtouse>`_

3. For RHEL 5 systems, subscribe to the following RHN channels:

 * MRG Messaging v. 1
 * MRG Messaging Base v. 1

4. QPID RPMs are not available in the default CentOS repositories. Instructions
   on building those RPMs can be found at :ref:`centos-build-qpid-rpms`.

Server
^^^^^^

1. Install the Pulp server and its dependencies.

::

  $ yum install pulp-rpm-server

2. Update ``/etc/pulp/server.conf`` to reflect the hostname of the server.

::

   [messaging]
   url: tcp://localhost:5672
   ...
   [server]
   server_name: localhost

.. warning::
 Red Hat Enterprise Linux 5

 The RHEL WSGI installation does not automatically enable the Apache module. This
 must be explicitly done by editing the ``/etc/httpd/conf.d/wsgi.conf`` file and
 uncommenting the ``LoadModule`` line. If Apache is already running when this change
 is made, it will need to be restarted. If it is not running, the pulp-server
 start script will start it automatically.

 SELinux needs to be disabled or set to permissive for RHEL-5.

3. Initialize Pulp, which starts and configures the database.

::

  $ service pulp-server init


.. warning::
  On new MongoDB installations, the start call may exit before the database is
  actually running. In these cases, this call will fail with an error about
  the connection failing. If this occurs, give MongoDB a few minutes to finish
  initializing and attempt this call again.

4. Start Pulp, which ensures the database is running, starts the message bus,
   and starts the web server.

::

  $ service pulp-server start

5. Optionally configure the server to automatically start on boot.

::

  $ chkconfig pulp-server on


Admin Client
^^^^^^^^^^^^

The Pulp Admin Client is used for administrative commands on the Pulp server,
such as the manipulation of repositories and content. The Pulp Admin Client can
be run on any machine that can access the Pulp server, including the server itself.
It is not a requirement that the admin client be run on a machine that is
configured as a Pulp consumer.

Pulp admin commands are accessed through the ``pulp-admin`` script.


1. Install the Pulp admin client packages:

::

  $ yum install pulp-rpm-admin-client

2. Update the admin client configuration to point to the Pulp server. Keep in mind
   that because of the SSL verification, this should be the fully qualified name of the server,
   even if it is the same machine (localhost will not work with the default apache generated SSL certificate).
   This change is made to the ``/etc/pulp/admin/admin.conf`` file:

::

  [server]
  host = localhost.localdomain


Consumer Client
^^^^^^^^^^^^^^^

The Pulp Consumer Client is present on all systems that wish to act as a consumer
of a Pulp server. The Pulp Consumer Client provides the means for a system to
register and configure itself with a Pulp server. Additionally, the Pulp Consumer
Client runs an agent that will receive messages and commands from the Pulp server.

Pulp consumer commands are accessed through the ``pulp-consumer script``. This
script must be run as root to permit access to add references to the Pulp server's
repositories.

1. Install the Pulp consumer client and agent packages:

::

  $ yum install pulp-rpm-consumer-client pulp-rpm-agent

2. Update the consumer client configuration to point to the Pulp server. Keep in mind
   that because of the SSL verification, this should be the fully qualified name of the server,
   even if it is the same machine (localhost will not work with the default Apache
   generated SSL certificate).
   This change is made to the ``/etc/pulp/consumer/consumer.conf`` file:

::

  [server]
  host = localhost.localdomain


3. Start the agent:

::

  $ service pulp-agent start
