:orphan:

.. _qpid-ssl-configuration:

Qpid SSL Configuration
======================

Overview
--------

The steps to reconfigure both Pulp and Qpid to communicate using SSL are as follows:

1. Generate x.509 keys, certificates and NSS database.
2. Edit the ``qpidd.conf`` file to require SSL and define certificates. Qpid 0.24+
   expects the config file to be at ``/etc/qpid/qpidd.conf`` and earlier Qpid versions
   expect it to be at ``/etc/qpidd.conf``.
3. Edit ``/etc/pulp/server.conf`` *messaging* section so that the server will connect to
   the Qpid broker using SSL.
4. On each consumer, edit ``/etc/pulp/consumer/consumer.conf`` *messaging* section
   so that the agent will connect to the Qpid broker using SSL.
5. Copy x.509 certificates to each consumer:

  * ``/etc/pki/pulp/qpid/ca.crt``
  * ``/etc/pki/pulp/qpid/client.crt``

6. Copy the x.509 certificates to each worker:

  * ``/etc/pki/pulp/qpid/ca.crt``
  * ``/etc/pki/pulp/qpid/client.crt``

7. Make sure the ``qpid-cpp-server-ssl`` RPM is installed.
8. Restart qpidd, httpd and pulp-agent


Details
-------

The steps in detail:

Step #1 - Create x.509 keys, certificates and NSS database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The recommended way to create the needed NSS DB and SSL certificates is to run the
``pulp-qpid-ssl-cfg`` script installed in /usr/bin. When installing into the default location
``/etc/pki/pulp/qpid``, users must run this script as root (or use sudo) due to the permissions
required to create files and directories within ``/etc/pki``. The script prompts for optional
user input but in all cases, a default is provided.

These inputs are as follows:

 *The output directory*
    The user may define the output directory in which the script will write the created
    NSS database and certificate files. The default location is: ``/etc/pki/pulp/qpid``.

 *The password for the NSS database*
     NSS databases are secured by specifying a password when they are created. All future
     access to the database for both read and writes will require this password. Users may
     enter a password or press <enter> to request that the script generate the password.

 *The CA certificate*
     The user has the opportunity to enter the path of an existing CA certificate or press
     <enter> to have a CA key and certificate generated. The CA certificate is used sign
     the generated client certificates used by the Qpid broker, the Pulp server and the
     consumer. All keys and certificates are stored in the NSS database.

The following is an example of running the script:

::

  # ./pulp-qpid-ssl-cfg

  Working in: /tmp/tmp23670


  Please specify a directory into which the created NSS database
  and associated certificates will be installed.

  Enter a directory [/etc/pki/pulp/qpid]:
  /etc/pki/pulp/qpid

  Please enter a password for the NSS database.  Generated if not specified.

  Enter a password:
  Using password: [27372]

  Please specify a CA.  Generated if not specified.

  Enter a path:

  Password file created.

  Database created.

  Creating CA certificate:


  Generating key.  This may take a few moments...

  CA created

  Creating BROKER certificate:


  Generating key.  This may take a few moments...

  Broker certificate created.

  Creating CLIENT certificate:


  Generating key.  This may take a few moments...

  Client certificate created.
  pk12util: PKCS12 EXPORT SUCCESSFUL
  MAC verified OK
  Client key & certificate exported

  Artifacts copied to: /etc/pki/pulp/qpid.

  Recommended properties in qpidd.conf:

  auth=no
  # SSL
  require-encryption=yes
  ssl-require-client-authentication=yes
  ssl-cert-db=/etc/pki/pulp/qpid/nss
  ssl-cert-password-file=/etc/pki/pulp/qpid/nss/password
  ssl-cert-name=broker
  ssl-port=5671
  ...


  Recommended properties in /etc/pulp/server.conf:

  ...
  [messaging]
  url: ssl://<host>:5671
  cacert: /etc/pki/pulp/qpid/ca.crt
  clientcert: /etc/pki/pulp/qpid/client.crt

  [tasks]
  broker_url: qpid://<host>:5671/
  celery_require_ssl: true
  cacert: /etc/pki/pulp/qpid/ca.crt
  keyfile: /etc/pki/pulp/qpid/client.crt
  certfile: /etc/pki/pulp/qpid/client.crt


  Recommended properties in /etc/pulp/consumer/consumer.conf:

  ...
  [messaging]
  scheme: ssl
  port: 5671
  cacert: /etc/pki/pulp/qpid/ca.crt
  clientcert: /etc/pki/pulp/qpid/client.crt


The following directory and files are created by the script:

* ``/etc/pki/pulp/qpid``
* ``/etc/pki/pulp/qpid/client.crt``
* ``/etc/pki/pulp/qpid/nss``
* ``/etc/pki/pulp/qpid/nss/cert8.db``
* ``/etc/pki/pulp/qpid/nss/password``
* ``/etc/pki/pulp/qpid/nss/secmod.db``
* ``/etc/pki/pulp/qpid/nss/key3.db``
* ``/etc/pki/pulp/qpid/broker.crt``
* ``/etc/pki/pulp/qpid/ca.crt``


Step #2 - Edit the Qpid broker configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, the Qpid broker (qpidd) is configured to accept non-encryped client connections
on port 5672. After creating the certificates and NSS database, qpidd needs to be
reconfigured to accept only SSL connections using the key and certificates stored in the
NSS database. The Qpid 0.24+ config file is located at ``/etc/qpid/qpidd.conf``, or for
earlier Qpid versions at ``/etc/qpidd.conf``. The ``qpidd.conf`` file needs to be edited
and the following SSL related properties defined as follows:

*auth*
    Require authentication. (value: no)

*require-encryption*
    Require all connections to use SSL. (value: yes)

*ssl-require-client-authentication*
    Require client SSL certificates for all SSL connections. (value: yes)

*ssl-cert-db*
    The fully qualified path to the NSS DB. (value: ``/etc/pki/pulp/qpid/nss``)

*ssl-cert-password-file*
    The fully qualified path to the password file used to access the NSS DB.
    (value: ``/etc/pki/pulp/qpid/nss/password``)

*ssl-cert-name*
    The name of the certificate in the NSS DB to be used by the qpid broker. (value: broker)

*ssl-port*
    The port to be use for SSL connections. (value: 5671)


Step #3 - Edit the Pulp server configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, the Pulp server is configured so that it will connect to the Qpid broker on port 5672.
Now that Qpid broker has been reconfigured to only accept SSL connections on port 5671, the
Pulp server configuration file, ``/etc/pulp/server.conf``, needs to be edited. The properties in
the *messaging* and *tasks* sections need to be updated.

The properties in the *messaging* section that specify the port, the CA certificate and client
certificate need to be updated as follows:

*url*
    The URL to the Qpid broker. Protocol choices: tcp=plain, ssl=SSL.
    (value: ssl://<host>:5671)

*cacert*
    The fully qualified path to the CA certificate used to validate the broker's
    SSL certificate. (value: ``/etc/pki/pulp/qpid/ca.crt``)

*clientcert*
    The fully qualified path a file containing both the client private key and certificate.
    The certificate is sent to the broker when the SSL connection is initiated by the Pulp
    server. The broker authenticates the Pulp server based on this certificate.
    (value: ``/etc/pki/pulp/qpid/client.crt``)

The following properties in the *tasks* section need to be updated as follows:

*broker_url*
    The URL that Celery will use to connect to the Qpid broker. Must specify the port 5671,
    and the correct host. (value: qpid://<host>:5671/)

*celery_require_ssl*
    Indicate that Pulps use of Celery should require SSL. (value: ``true``)

*cacert*
    The fully qualified path to the CA certificate used to validate the broker's SSL
    certificate. (value: ``/etc/pki/pulp/qpid/ca.crt``)

*keyfile*
    The fully qualified path to the key file associated with the client's certificate. The
    ``pulp-qpid-ssl-cfg`` script puts the key in the same file as the client certificate file.
    (value: ``/etc/pki/pulp/qpid/client.crt``)

*certfile*
    The fully qualified path to the certificate file associated with the client, and corresponding
    with the key specified by keyfile. (value: ``/etc/pki/pulp/qpid/client.crt``)


Step #4 - Edit each consumer configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, the Pulp consumer is configured so that it will connect to the Qpid broker on port 5672.
Now that the Qpid broker has been reconfigured to only accept SSL connections on port 5671, the
Pulp consumer configuration file, ``/etc/pulp/consumer/consumer.conf``, needs to be edited.
The properties in the *messaging* section that specify the port, the CA certificate and
client certificate need to be updated as follows:

*scheme*
    The protocol used in the URL. (value: ssl)

*port*
    The TCP port number. (value: 5671)

*cacert*
    The fully qualified path to the CA certificate used to validate the broker's SSL
    certificate. (value: ``/etc/pki/pulp/qpid/ca.crt``)

*clientcert*
    The fully qualified path a file containing both the client private key and certificate.
    The certificate is sent to the broker when the SSL connection is initiated by the
    consumer. The broker authenticates the consumer based on this certificate.
    (value: ``/etc/pki/pulp/qpid/client.crt``)


Step #5 - Copy certificates to each consumer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In step #4, we updated the consumer.conf and specified the SSL properties which included
the paths to the CA and client certificate files. Those files need to be copied to each
consumer.

For example:

::

 cd ``/etc/pki/pulp/qpid``
 scp ca.crt root@<host>:/etc/pki/pulp/qpid
 scp client.crt root@<host>:/etc/pki/pulp/qpid

**Note:** the <host> is the hostname of a consumer.


Step #6 - Copy certificates to each worker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In step #3, we updated the ``server.conf`` and specified the SSL properties which included
the paths to the CA and client certificate files. Those files need to be copied to each
worker.

For example:

::

 cd ``/etc/pki/pulp/qpid``
 scp ca.crt root@<host>:/etc/pki/pulp/qpid
 scp client.crt root@<host>:/etc/pki/pulp/qpid

**Note:** the <host> is the hostname of a worker.


Step #7 - Install qpid-cpp-server-ssl
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To support SSL, the Qpid broker must have the SSL module installed. This module
is provided by the ``qpid-cpp-server-ssl`` package. Make sure this package is installed.


Step #8 - Restart services
^^^^^^^^^^^^^^^^^^^^^^^^^^

Now that the Qpid and pulp configurations have been updated, the corresponding services
need to be restarted.

On the Pulp server:

* qpidd
* httpd
* pulp_resource_manager
* pulp_celerybeat

On each worker:

* pulp_workers

On each consumer:

* pulp-agent


Troubleshooting
---------------

Here are a few troubleshooting tips:


General
^^^^^^^

#. The Pulp server logs to syslog.

#. The Qpid broker (qpidd) also logs to syslog by default.

#. The consumer agent (goferd) logs Qpid connection information to syslog.
   See: :ref:`logging` for details.

#. Make sure you've copied the client key and certificate to each consumer.

#. Make sure you have restarted the services involved: httpd, qpidd, pulp_celerybeat,
   pulp_resource_manager, pulp_workers, and pulp-agent.

#. Make sure the firewall on the Pulp server is configured to permit TCP on port 5671
   or that it's disabled.

#. Make sure that the pulp-selinux RPM is installed on the Pulp server.


Log Messages Explained
^^^^^^^^^^^^^^^^^^^^^^

``connection refused``
   Log messages containing ``connection refused`` most likely indicate firewall and/or
   SELinux problems and not SSL issues.

``[Security] notice Listening for SSL connections on TCP port 5671``
    If you don't see a log message containing this in your syslog, then either the
    ``qpid-cpp-server-ssl`` package is not installed or the Qpid broker is not configured
    for SSL. This can also indicate that SSL configuration is complete but the Qpid broker
    service (qpidd) needs to be restarted.

``[Security] notice SSL plugin not enabled, you must set --ssl-cert-db to enable it.``
    Log messages containing this indicate that the Qpid broker has
    been configured for SSL but the ``qpid-cpp-server-ssl`` RPM has not been installed.
    This can also indicate that the RPM has been installed but that the Qpid service (qpidd)
    needs to be restarted.

``[Security] error Rejected un-encrypted connection.``
    Log messages containing this indicate that either the Pulp
    server or the consumer is not properly configured to connect using SSL. This can also
    indicate that SSL configuration is complete but that either the Pulp server (httpd) or
    the consumer agent (goferd) needs to be restarted.


Helpful Links
-------------

* `<​http://www.mail-archive.com/qpid-commits@incubator.apache.org/msg06212.html>`_
* `<​http://www.mozilla.org/projects/security/pki/nss/tools/certutil.html>`_
