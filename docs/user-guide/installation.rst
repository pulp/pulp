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

* RHEL 6 & 7
* Fedora 19 & 20
* CentOS 6 & 7

Consumer

* RHEL 5, 6, & 7
* Fedora 19 & 20
* CentOS 5, 6 & 7

Admin Client

* RHEL 6 & 7
* Fedora 19 & 20
* CentOS 6 & 7

Prerequisites
-------------

* The following ports must be open into the server:

 * 80 for consumers to access repositories served over HTTP
 * 443 for consumers to access repositories served over HTTPS
 * 443 for clients (both admin and consumer) to access Pulp APIs
 * 5672 for consumers to connect to the message bus if it is left unsecured
 * 5671 for consumers to connect to the message bus if it is running over HTTPS

* The mod_python Apache module must be uninstalled or not loaded. Pulp uses
  mod_wsgi which conflicts with mod_python and will cause the server to fail.

.. warning::
  The python-qpid package is not available from Pulp installation repositories
  on RHEL 5 or CentOS 5. This will prevent management of RHEL 5 or CentOS 5
  clients with pulp-consumer using Qpid. Users who want to use Qpid instead of
  RabbitMQ and manage these RHEL 5 or CentOS 5 clients will need to build
  python-qpid from source.
  

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

2. For RHEL and CentOS systems, the EPEL repositories are required. Following commands will add the
   appropriate repositories for RHEL6 and RHEL7 respectively:

   RHEL6::

    $ sudo rpm -Uvh https://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm

   RHEL7::

    $ sudo rpm -Uvh https://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-2.noarch.rpm

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

   You need mongodb-server with version >= 2.4 installed for Pulp server. It is highly recommended
   that you `configure MongoDB to use SSL`_. If you are using Mongo's authorization feature, you
   will need to grant the ``readWrite`` and ``dbAdmin`` roles to the user you provision for Pulp to
   use. The ``dbAdmin`` role allows Pulp to create collections and install indices on them.

.. _configure MongoDB to use SSL: http://docs.mongodb.org/v2.4/tutorial/configure-ssl/#configure-mongod-and-mongos-for-ssl

   After installing MongoDB, you should configure it to start at boot and start it. For Upstart
   based systems::

    $ sudo service mongod start
    $ sudo chkconfig mongod on

   For systemd based systems::

    $ sudo systemctl enable mongod
    $ sudo systemctl start mongod

   .. warning::
      On new MongoDB installations, MongoDB takes some time to preallocate large files and will not
      accept connections until it finishes. When this happens, Pulp will wait for MongoDB to
      become available before starting.


#. You must also provide a message bus for Pulp to use. Pulp will work with Qpid or RabbitMQ, but
   is tested with Qpid, and uses Qpid by default. This can be on the same host that you will
   run Pulp on, or elsewhere as you please. To install Qpid on a yum based system, use
   this command::
    
    $ sudo yum install qpid-cpp-server qpid-cpp-server-store

   .. note::
      In environments that use Qpid, the ``qpid-cpp-server-store`` package provides durability, a
      feature that saves broker state if the broker is restarted. This is a required feature for
      the correct operation of Pulp. Qpid provides a higher performance durability package named
      ``qpid-cpp-server-linearstore`` which can be used instead of ``qpid-cpp-server-store``, but
      may not be available on all versions of Qpid. If ``qpid-cpp-server-linearstore`` is available
      in your environment, consider uninstalling ``qpid-cpp-server-store`` and installing
      ``qpid-cpp-server-linearstore`` instead for improved broker performance. After installing
      this package, you will need to restart the Qpid broker to enable the durability feature.

   Pulp uses the ``ANONYMOUS`` Qpid authentication mechanism by default. To
   enable username/password-based ``PLAIN`` broker authentication, you will need
   to configure SASL with a username/password, and then configure Pulp to use that
   username/password. Refer to the Qpid docs on how to configure username/password
   authentication using SASL. Once the broker is configured, configure Pulp according
   to the docs on using
   :ref:`Pulp with Qpid and username/password authentication <pulp-broker-qpid-with-username-password>`.

   The server can be *optionally* configured so that it will connect to the broker using SSL by following the steps
   defined in the :ref:`Qpid SSL Configuration Guide <qpid-ssl-configuration>`. By default, Pulp
   does not expect to use SSL and will connect to the broker using a plain TCP connection to localhost.

   After installing and configuring Qpid, you should configure it to start at boot and start it. For
   Upstart based systems::

    $ sudo service qpidd start
    $ sudo chkconfig qpidd on

   For systemd based systems::

    $ sudo systemctl enable qpidd
    $ sudo systemctl start qpidd

#. Install the Pulp server, task workers, and their dependencies. For Pulp installations that use
   Qpid, install Pulp server using::

    $ sudo yum groupinstall pulp-server-qpid

   .. warning::
      The Pulp team believes that Pulp's webserver and Celery workers can be deployed across several
      machines (with load balancing for the HTTP requests), but this has not been formally tested by
      our Quality Engineering team. We encourage feedback if you have tried this, positive or
      negative. If you wish to try this, each host that participates in the distributed Pulp
      application will need to have access to a shared /var/lib/pulp filesystem, including the web
      servers and the task workers. It is important that the httpd and celery processes are run by
      users with identical UIDs and GIDs for permissions on the shared filesystem.

   .. note::
      For RabbitMQ installations, install Pulp server without any Qpid specific libraries using
      ``sudo yum groupinstall pulp-server``. You may need to install additional RabbitMQ
      dependencies manually.

#. Edit ``/etc/pulp/server.conf``. Most defaults will work, but these are sections you might
   consider looking at before proceeding. Each section is documented in-line.

   * **email** if you intend to have the server send email (off by default)
   * **database** if your database resides on a different host or port. It is strongly recommended
                  that you set ssl and verify_ssl to True.
   * **messaging** if your message broker for communication between Pulp components is on a
     different host or if you want to use SSL. For more information on this section refer to the
     :ref:`Pulp Broker Settings Guide <pulp-broker-settings>`.
   * **tasks** if your message broker for asynchronous tasks is on a different host or if you want
     to use SSL. For more information on this section refer to the
     :ref:`Pulp Broker Settings Guide <pulp-broker-settings>`.
   * **security** to provide your own SSL CA certificates, which is a good idea if you intend to use
     Pulp in production
   * **server** if you want to change the server's URL components, hostname, or default credentials

#. Initialize Pulp's database. It is important that the broker is running before initializing
   Pulp's database. It is also important to do this before starting Apache or any Pulp services.
   The database initialization needs to be run as the ``apache`` user, which can be done by
   running::

   $ sudo -u apache pulp-manage-db

  .. note::
      If Apache or Pulp services are already running, restart them after running the
      ``pulp-manage-db`` command.

  .. warning::
     It is recommended that you configure your web server to refuse SSLv3.0. In Apache, you can do
     this by editing ``/etc/httpd/conf.d/ssl.conf`` and configuring the ``SSLProtocol`` directive
     like this::

        `SSLProtocol all -SSLv2 -SSLv3`

#. Start Apache httpd and set it to start on boot. For Upstart based systems::

    $ sudo service httpd start
    $ sudo chkconfig httpd on

   For systemd based systems::

    $ sudo systemctl enable httpd
    $ sudo systemctl start httpd

   .. _distributed_workers_installation:

#. Pulp has a distributed task system that uses `Celery <http://www.celeryproject.org/>`_.
   Begin by configuring, enabling and starting the Pulp workers. To configure the workers, edit
   ``/etc/default/pulp_workers``. That file has inline comments that explain how to use each
   setting. After you've configured the workers, it's time to enable and start them. For Upstart
   systems::

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
   once each (i.e., do not enable either of these on any more than one Pulp server).

   .. warning::
      
      ``pulp_celerybeat`` and ``pulp_resource_manager`` must both be singletons, so be sure that you
      only enable each of these on one host if you are experimenting with Pulp's untested HA
      deployment. They do not have to run on the same host, however.

   On some Pulp system, configure, start and enable the Celerybeat process. This process performs a
   job similar to a cron daemon for Pulp. Edit ``/etc/default/pulp_celerybeat`` to your liking, and
   then enable and start it. Again, do not enable this on more than one host. For Upstart::

      $ sudo chkconfig pulp_celerybeat on
      $ sudo service pulp_celerybeat start

   For systemd::

      $ sudo systemctl enable pulp_celerybeat
      $ sudo systemctl start pulp_celerybeat

   Lastly, one ``pulp_resource_manager`` process must be running in the installation. This process
   acts as a task router, deciding which worker should perform certain types of tasks. Apologies
   for the repetitive message, but it is important that this process only be enabled on one host.
   Edit ``/etc/default/pulp_resource_manager`` to your liking. Then, for upstart::

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

Consumer Client And Agent
-------------------------

The Pulp Consumer Client is present on all systems that wish to act as a consumer
of a Pulp server. The Pulp Consumer Client provides the means for a system to
register and configure itself with a Pulp server. Additionally, the Pulp Consumer
Client runs an agent that will receive messages and commands from the Pulp server.

Pulp consumer commands are accessed through the ``pulp-consumer`` script. This
script must be run as root to permit access to add references to the Pulp server's
repositories.

1. For environments that use Qpid, install the Pulp consumer client, agent packages, and Qpid
specific consumer dependencies with one command by running:

::

   $ sudo yum groupinstall pulp-consumer-qpid


.. note::

     For RabbitMQ installations, install the Pulp consumer client and agent packages without any
     Qpid specific dependencies using ``sudo yum groupinstall pulp-consumer``. You may need to
     install additional RabbitMQ dependencies manually including the ``python-gofer-amqplib``
     package.


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


4. Set the agent to start at boot.  For upstart::

      $ sudo chkconfig goferd on
      $ sudo service goferd start

   For systemd::

      $sudo systemctl enable goferd
      $sudo systemctl start goferd


SSL Configuration
-----------------

By default, all of the client components of Pulp will require validly signed SSL certificates from
the servers on remote ends of its outbound connections. On a brand new httpd installation, a
self-signed certificate will be generated for the server to use to serve Pulp. This means that a
fresh installation will experience client errors similar to this::

    (pulp)[rbarlow@coconut pulp]$ pulp-admin puppet repo list
    +----------------------------------------------------------------------+
    Puppet Repositories
    +----------------------------------------------------------------------+

    WARNING: The server's SSL certificate is untrusted!

    The server's SSL certificate was not signed by a trusted authority. This could
    be due to a man-in-the-middle attack, or it could be that the Pulp server needs
    to have its certificate signed by a trusted authority. If you are willing to
    accept the associated risks, you can set verify_ssl to False in the client
    config's [server] section to disable this check.

You have two choices to solve this issue: You may make or acquire signed SSL certificates for httpd
to use to serve Pulp, or you may configure Pulp's various clients not to perform SSL signature
validation.

.. note:
   
   Even Pulp's server makes client connections in some cases. For example, a Child Node will act as
   a client to its parent.

.. _signed certificates:

Signed Certificates
^^^^^^^^^^^^^^^^^^^

If you wish to use signed certificates, you must decide whether you will purchase signed
certificates from a root certificate authority or use your own organization's certificate authority.
How to make or buy signed certificates is outside the scope of this document. We will assume that
you have these items:

#. A PEM-encoded X.509 certificate file, signed by a trusted certificate authority.
#. A PEM-encoded private key file that corresponds to your SSL certificate.
#. The CA certificate that signed your SSL certificate. This is only necessary if your Linux
   distribution does not already include the CA that signed your certificate in its system CA
   pack.

You must first configure httpd to use the SSL certificate and private key you have acquired. You
must configure the `SSLCertificateFile`_ and `SSLCertificateKeyFile`_ mod_ssl directives to point at
these files. On Red Hat based systems, these settings can be found in
``/etc/httpd/conf.d/ssl.conf``.

.. _SSLCertificateFile: https://httpd.apache.org/docs/2.2/mod/mod_ssl.html#sslcertificatefile
.. _SSLCertificateKeyFile: https://httpd.apache.org/docs/2.2/mod/mod_ssl.html#sslcertificatekeyfile

If you are using a CA certificate that is not already trusted by your operating system's system CA
pack, you may either configure Pulp to trust that CA, or you may configure your operating system to
trust that CA.

Pulp has a setting called ``ca_path`` in these files: ``/etc/pulp/admin/admin.conf``,
``/etc/pulp/consumer/consumer.conf``, and ``/etc/pulp/nodes.conf``. This setting indicates which CA
pack each of these components should use when validating Pulp server certificates. By default, Pulp
will use the operating system's CA pack. If you wish, you may adjust this setting to point to a
different CA pack. The CA pack may be a single file that contains multiple concatenated
certificates, or it may be a directory with OpenSSL style hashed symlinks pointing at CA certificate
files, with one certificate per file. Of course, if you have exactly one CA certificate, you can
configure this setting to point at it directly.

There are three settings in ``/etc/pulp/server.conf`` that you should be aware of, but probably
should not alter. ``capath`` and ``cakey`` point to a CA certificate and key that Pulp uses to sign
client authentication certificates. Note that this is not the CA that you signed your server
certificate with earlier. It is used only internally by Pulp and Apache to create client
certificates with login calls, and to validate those certificates when clients use the API. It is
best to avoid altering these settings. The third setting is confusingly named
``ssl_ca_certificate``. This setting should not be used, since it causes a chicken and egg situation
that could cause the universe to experience a machine check exception. If it is configured, the yum
consumer handlers will use this CA in their yum repository files for validating the Pulp server. The
problem is that the consumer must have already trusted Pulp in order to have registered to Pulp to
get this CA file, which helps the consumer to trust Pulp. It's best for users to configure CA trust
themselves outside of Pulp, which is why this setting should not be used.

.. warning::

   The Pulp team plans to deprecate the ``capath``, ``cakey``, and ``ssl_ca_certificate`` settings.
   It is best to avoid altering these settings from their defaults, as described above. See
   `1123509`_ and `1165403`_.

.. _1123509: https://bugzilla.redhat.com/show_bug.cgi?id=1123509
.. _1165403: https://bugzilla.redhat.com/show_bug.cgi?id=1165403

If you want to use SSL with Qpid, see the
:ref:`Qpid SSL Configuration Guide <qpid-ssl-configuration>`.

Turning off Validation
^^^^^^^^^^^^^^^^^^^^^^

.. warning::
   
   It is strongly recommended that you make or acquire :ref:`signed certificates` to prevent
   man-in-the-middle attacks or other nefarious activities. It is very risky to assume that the
   other end of the connection is who they claim to be. SSL uses a combination of encryption and
   authentication to ensure private communication. Disabling these settings removes the
   authentication component from the SSL session, which removes the guarantee of private
   communication since you can't be sure who you are communicating with.

Pulp has a setting called ``verify_ssl`` in these files: ``/etc/pulp/admin/admin.conf``,
``/etc/pulp/consumer/consumer.conf``, ``/etc/pulp/nodes.conf``, and ``/etc/pulp/repo_auth.conf``. If
you configure these settings to false, the respective Pulp components will no longer validate the
Pulp server's certificate signature.

Pulp Broker Settings
--------------------

To configure Pulp to work with a non-default broker configuration read the
:ref:`Pulp Broker Settings Guide <pulp-broker-settings>`.

MongoDB Authentication
----------------------

To configure Pulp for connecting to the MongoDB with username/password authentication, use the
following steps:
1. Configure MongoDB for username password authentication. See
`MongoDB - Enable Authentication <http://docs.mongodb.org/manual/tutorial/enable-authentication/>`_
for details.
2. In ``/etc/pulp/server.conf``, find the ``[database]`` section and edit the ``username`` and
``password`` values to match the user configured in step 1.
3. Restart the httpd service
::

  $ sudo service httpd restart

