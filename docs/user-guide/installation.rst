Installation
============

Pulp operates with three main components that get installed potentially on different
machines.

Server
  This is the main application server that stores data and distributes content.

Agent
  This component runs on consumers and communicates with the server to provide remote content
  management.

Client
  This is a command line component that comes as two pieces: admin-client,
  which manages the server; and consumer-client, which manages a consumer's relationship
  to the server. admin-client can be run from any machine that can access the server's
  REST API, but the consumer-client must be run on a consumer.

Additional steps are needed for upgrading Pulp 1.1 installations. More information can be found
in the :doc:`v1_upgrade` section of this guide.


Supported Operating Systems
---------------------------
Server

* RHEL 6
* Fedora 19 & 20
* CentOS 6

Consumer

* RHEL 5 & 6
* Fedora 19 & 20
* CentOS 5 & 6

Prerequisites
-------------

* On RHEL 5, Pulp does not currently work with SELinux. SELinux must be
  set to Permissive or Disabled.
* The following ports must be open into the server:

 * 80 for consumers to access repositories served over HTTP
 * 443 for consumers to access repositories served over HTTPS
 * 443 for clients (both admin and consumer) to access Pulp APIs
 * 5672 for consumers to connect to the message bus if it is left unsecured
 * 5671 for consumers to connect to the message bus if it is running over HTTPS

* The mod_python Apache module must be uninstalled or not loaded. Pulp uses
  mod_wsgi which conflicts with mod_python and will cause the server to fail.

.. warning::
  MongoDB is known to have
  `serious limitations <http://docs.mongodb.org/manual/faq/fundamentals/#what-are-the-32-bit-limitations>`_
  on 32-bit architectures. It is strongly advised that you run MongoDB on a 64-bit architecture.

Storage Requirements
--------------------

The MongoDB database can easily grow to 10GB or more in size, which vastly
exceeds the amount of data actually stored in the database. This is normal
(but admittedly surprising) behavior for MongoDB. As such, make sure you
allocate plenty of storage within ``/var/lib/mongodb``.

Repositories
------------

1. Download the appropriate repo definition file from the Pulp repository:

 * Fedora: http://repos.fedorapeople.org/repos/pulp/pulp/fedora-pulp.repo
 * RHEL: http://repos.fedorapeople.org/repos/pulp/pulp/rhel-pulp.repo

2. For RHEL and CentOS systems, the EPEL repositories are required. More information can
   be found at: `<http://fedoraproject.org/wiki/EPEL/FAQ#howtouse>`_

3. For RHEL 5 systems, subscribe to the following RHN channels:

 * MRG Messaging v. 1
 * MRG Messaging Base v. 1

4. Qpid RPMs are not available in the default CentOS repositories for CentOS
   releases 6.2 and earlier. Instructions on building those RPMs can be found
   at :ref:`centos-build-qpid-rpms`.


.. _server_installation:

Server
------

#. You must provide a running MongoDB instance for Pulp to use. You can use the same host that you
   will run Pulp on, or you can give MongoDB its own separate host if you like. You can even use
   MongoDB replica sets if you'd like to have higher availability. For yum based systems, you can
   install MongoDB with this command::

    $ sudo yum install mongodb-server

   After installing MongoDB, you should configure it to start at boot and start it. For Upstart
   based systems::

    $ sudo service mongod start
    $ sudo chkconfig mongod on

   For systemd based systems::

    $ sudo systemctl enable mongod
    $ sudo systemctl start mongod

   .. warning::
      On new MongoDB installations, the start call may exit before the database is
      accepting connections. MongoDB takes some time to preallocate large files and will not accept
      connections until it finishes. When this happens, it is possible for Pulp to fail to start.
      If this occurs, give MongoDB a few minutes to finish initializing and start Pulp again.

#. You must also provide a running Qpid instance for Pulp to use. This can also be on the same host
   that you will run Pulp on, or it can be elsewhere as you please. For yum based systems, you can
   install Qpid with this command::
    
    $ sudo yum install qpid-cpp-server

   Configure the Qpid broker in ``/etc/qpidd.conf`` and either add or change the auth setting
   to be off by having ``auth=no`` on its own line.  The server can be *optionally* configured
   so that it will connect to the broker using SSL by following the steps defined in the
   :ref:`Qpid SSL Configuration Guide <qpid-ssl-configuration>`.  By default, the server
   will connect using a plain TCP connection.

   After installing and configuring Qpid, you should configure it to start at boot and start it. For
   Upstart based systems::

    $ sudo service qpidd start
    $ sudo chkconfig qpidd on

   For systemd based systems::

    $ sudo systemctl enable qpidd
    $ sudo systemctl start qpidd

#. Install the Pulp server, task workers, and their dependencies. This step may be performed on more
   than one host if you wish to scale out either Pulp's task workers, or its HTTP interface with a
   load balancer::

    $ sudo yum groupinstall pulp-server

   .. warning::
      Each host that participates in the distributed Pulp application will need to have access to a
      shared /var/lib/pulp filesystem, including both the web servers and the task workers.

#. For each host that you've installed the Pulp server on, edit ``/etc/pulp/server.conf``. Most
   defaults will work, but these are sections you might consider looking at before proceeding. Each
   section is documented in-line.

   * **email** if you intend to have the server send email (off by default)
   * **database** if your database resides on a different host or port
   * **messaging** if your Qpid server is on a different host or if you want to use SSL
   * **security** to provide your own SSL CA certificates, which is a good idea if you intend to use
     Pulp in production
   * **server** if you want to change the server's URL components, hostname, or default credentials

#. Initialize Pulp's database. It's important to do this before starting Apache or the task workers,
   but you only need to perform this step on one host that has the server package installed. If
   Apache or the workers are already running, just restart them::

   $ sudo pulp-manage-db

#. For each Pulp host that you wish to handle HTTP requests, start Apache httpd and set it to start
   on boot. For Upstart based systems::

    $ sudo service httpd start
    $ sudo chkconfig httpd on

   For systemd based systems::

    $ sudo systemctl enable httpd
    $ sudo systemctl start httpd

   .. _distributed_workers_installation:

#. Pulp has a distributed task system that uses `Celery <http://www.celeryproject.org/>`_.
   Begin by configuring, enabling and starting the Pulp workers on each host that you wish to
   perform distributed tasks with. To configure the workers, edit ``/etc/default/pulp_workers``.
   That file has inline comments that explain how to use each setting. After you've configured the
   workers, it's time to enable and start them. For Upstart systems::

      $ sudo chkconfig pulp_workers on
      $ sudo service pulp_workers start

   For systemd systems::

      $ sudo systemctl enable pulp_workers
      $ sudo systemctl start pulp_workers

   .. note::

      The pulp_workers systemd unit does not actually correspond to the workers, but it runs a
      script that dynamically generates units for each worker, based on the configured concurrency
      level. You can check on the status of those generated workers by using the
      ``systemctl status`` command. The workers are named with the template
      ``pulp_worker-<number>``, and they are numbered beginning with 0 and up to
      ``PULP_CONCURRENCY - 1``. For example, you can use ``sudo systemctl status pulp_worker-1`` to
      see how the second worker is doing.

#. There are two more services that need to be running, but it is important that these two only run
   once each (i.e., do not enable either of these on any more than one Pulp server!)

   .. warning::
      
      ``pulp_celerybeat`` and ``pulp_resource_manager`` must both be singletons, so be sure that you
      only enable each of these on one host. They do not have to run on the same host, however.

   One some Pulp system, configure, start and enable the Celerybeat process. This process performs a
   job similar to a cron daemon for Pulp. Edit ``/etc/default/pulp_celerybeat`` to your liking, and
   then enable and start it. Again, do not enable this on more than one host. For Upstart::

      $ sudo chkconfig pulp_celerybeat on
      $ sudo service pulp_celerybeat start

   For systemd::

      $ sudo systemctl enable pulp_celerybeat
      $ sudo systemctl start pulp_celerybeat

   Lastly, we also need one ``pulp_resource_manager`` process running in the installation. This
   process acts as a task router, deciding which worker should perform certain types of tasks.
   Apologies for the repetitive message, but it is important that this process only be enabled on
   one host. Edit ``/etc/default/pulp_resource_manager`` to your liking. Then, for upstart::

      $ sudo chkconfig pulp_resource_manager on
      $ sudo service pulp_resource_manager start

   For systemd::

      $ sudo systemctl enable pulp_resource_manager
      $ sudo systemctl start pulp_resource_manager

Admin Client
------------

The Pulp Admin Client is used for administrative commands on the Pulp server,
such as the manipulation of repositories and content. The Pulp Admin Client can
be run on any machine that can access the Pulp server's REST API, including the
server itself. It is not a requirement that the admin client be run on a machine
that is configured as a Pulp consumer.

Pulp admin commands are accessed through the ``pulp-admin`` script.


1. Install the Pulp admin client packages:

::

  $ sudo yum groupinstall pulp-admin

2. Update the admin client configuration to point to the Pulp server. Keep in mind
   that because of the SSL verification, this should be the fully qualified name of the server,
   even if it is the same machine (localhost will not work with the default apache
   generated SSL certificate). Regardless, the "host" setting below must match the
   "CN" value of the server's HTTP SSL certificate.
   This change is made globally to the ``/etc/pulp/admin/admin.conf`` file, or
   for one user in ``~/.pulp/admin.conf``:

::

  [server]
  host = localhost.localdomain



.. _consumer_installation:

Consumer Client
---------------

The Pulp Consumer Client is present on all systems that wish to act as a consumer
of a Pulp server. The Pulp Consumer Client provides the means for a system to
register and configure itself with a Pulp server. Additionally, the Pulp Consumer
Client runs an agent that will receive messages and commands from the Pulp server.

Pulp consumer commands are accessed through the ``pulp-consumer`` script. This
script must be run as root to permit access to add references to the Pulp server's
repositories.

1. Install the Pulp consumer client and agent packages:

::

  $ sudo yum groupinstall pulp-consumer

2. Update the consumer client configuration to point to the Pulp server. Keep in mind
   that because of the SSL verification, this should be the fully qualified name of the server,
   even if it is the same machine (localhost will not work with the default Apache
   generated SSL certificate). Regardless, the "host" setting below must match the
   "CN" value of the server's HTTP SSL certificate.
   This change is made to the ``/etc/pulp/consumer/consumer.conf`` file:

::

  [server]
  host = localhost.localdomain


3. The agent may be configured so that it will connect to the Qpid broker using SSL by
   following the steps defined in the :ref:`Qpid SSL Configuration Guide <qpid-ssl-configuration>`.
   By default, the agent will connect using a plain TCP connection.

4. Set the agent to start at boot:

::

  $ sudo chkconfig pulp-agent on

5. Start the agent:

::

  $ sudo service pulp-agent start


SSL Configuration
-----------------

To try out Pulp, the default SSL configuration should work well. However,
when deploying Pulp in production, you should supply your own SSL certificates.

In ``/etc/pulp/server.conf``, find the ``[security]`` section. There is good
documentation in-line, but make sure in particular that ``cacert`` and ``cakey``
point to the certificate and private key that you want Apache to use for HTTPS.
Also make sure that Apache's config in ``/etc/httpd/conf.d/pulp.conf`` matches
these settings. If you plan to use Pulp's consumer features, set ``ssl_ca_certificate``.

If you want to use SSL with Qpid, see the
:ref:`Qpid SSL Configuration Guide <qpid-ssl-configuration>`.

MongoDB Authentication
----------------------

To configure pulp for connecting to the MongoDB with username/password authentication, use the
following steps:
1. Configure MongoDB for username password authentication.  See
`MongoDB - Enable Authentication <http://docs.mongodb.org/manual/tutorial/enable-authentication/>`_
for details.
2. In ``/etc/pulp/server.conf``, find the ``[database]`` section and edit the ``username`` and
``password`` values to match the user configured in step 1.
3. Restart the httpd service
::

  $ sudo service httpd restart


