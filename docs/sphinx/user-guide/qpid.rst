QPID Configuration
==================

Overview
--------

The steps to reconfigure both Pulp and QPID to communicate using SSL are as follows:

 1. Generate x.509 keys, certificates and NSS database.
 2. Edit /etc/qpidd.conf to require SSL and define certificates.
 3. Edit /etc/pulp/server.conf *messaging* section to connect to the QPID broker using SSL.
 4. On each consumer, edit /etc/pulp/consumer/consumer.conf *messaging* section
    to connect to the QPID broker using SSL.
 5. Copy x.509 certificates to each consumer:

   * /etc/pki/pulp/qpid/ca.crt
   * /etc/pki/pulp/qpid/client.crt

 6. Make sure qpid-cpp-server-ssl is installed.
 7. Restart qpidd, httpd and pulp-agent


Step #1 - Create x.509 keys, certificates and NSS database
----------------------------------------------------------

The recommended way to create the needed NSS DB and SSL certificates, is to run the
pulp-qpid-ssl-cfg script installed in /usr/bin.  When installing into the default location
/etc/pki/pulp/qpid, users must run this script as root (or use sudo) due to the permissions
required to create files and directories within /etc/pki.  The script prompts for optional
user input but in all cases, a default is provided.

These inputs are as follows:

 *The output directory* - The user may define the output directory in which the script
 will write the created NSS database and certificate files.  The default location is:
 /etc/pki/pulp/qpid.

 *The password for the NSS database*
     NSS databases are secured by specifying a password
     when they are created.  All future access to the database for both read and writes will
     require this password.  Users may enter a password or press <enter> to request that the
     script generate the password.

 *The CA certificate*
     The user has the opportunity to enter the path of an existing
     CA certificate or press <enter> to have a CA key and certificate generated.  The CA
     certificate is used sign the generated client certificates usednby the QPID broker, the
     Pulp server and the Consumer.  All keys and certificates are stored in the NSS database.

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

  Recommended properties in /etc/qpidd.conf:

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
  url=ssl://<host>:5671
  cacert=/etc/pki/pulp/qpid/ca.crt
  clientcert=/etc/pki/pulp/qpid/client.crt


  Recommended properties in /etc/pulp/consumer/consumer.conf:

  ...
  [messaging]
  scheme=ssl
  port=5671
  cacert=/etc/pki/pulp/qpid/ca.crt
  clientcert=/etc/pki/pulp/qpid/client.crt


The following directory and files are created by the script:

  * /etc/pki/pulp/qpid
  * /etc/pki/pulp/qpid/client.crt
  * /etc/pki/pulp/qpid/nss
  * /etc/pki/pulp/qpid/nss/cert8.db
  * /etc/pki/pulp/qpid/nss/password
  * /etc/pki/pulp/qpid/nss/secmod.db
  * /etc/pki/pulp/qpid/nss/key3.db
  * /etc/pki/pulp/qpid/broker.crt
  * /etc/pki/pulp/qpid/ca.crt


Step #2 - Edit the QPID broker configuration
--------------------------------------------

By default, qpidd is configured to accept non-encryped client connections on port 5672.
After creating the certificates and NSS database, qpidd needs to be reconfigured to accept
only SSL connections using the key and certificates stored in the NSS database.  The
/etc/qpidd.conf needs to be edited and the following SSL related properties defined
as follows:

*auth*
    Require authentication. (value: no)

*require-encryption*
    Require all connections to use SSL. (value: yes)

*ssl-require-client-authentication*
    Require client SSL certificates for all SSL connections. (value: yes)

*ssl-cert-db*
    The fully qualified path to the NSS DB. (value: /etc/pki/pulp/qpid/nss)

*ssl-cert-password-file*
    The fully qualified path to the password file used to access the NSS DB.
    (value: /etc/pki/pulp/qpid/nss/password)

*ssl-cert-name*
    The name of the certificate in the NSS DB to be used by the qpid broker. (value: broker)

*ssl-port*
    The port to be use for SSL connections. (value: 5671)


Step #3 - Edit pulp server configuration
----------------------------------------

By default, the Pulp server is configured to connect to the QPID broker on port 5672.
Now that qpidd has been reconfigured to only accept SSL connections on port 5671, the
Pulp server configuration file (/etc/pulp/server.conf) needs to be edited.  The properties
in the *messaging* section that specify the port, the CA certificate and client certificate
need to be updated as follows:

*url*
    The URL to the qpid broker. Protocol choices: tcp=plain, ssl=SSL.
    (value: ssl://<host>:5671)

*cacert*
    The fully qualified path to the CA certificate used to validate the broker
    (value: /etc/pki/pulp/qpid/ca.crt)

*clientcert*
    The fully qualified path a file containing both the client private key and certificate.
    (value: /etc/pki/pulp/qpid/client.crt)

Step #4 - Edit consumer configuration
-------------------------------------

By default, the Pulp consumer is configured to connect to the QPID broker on port 5672.
Now that qpidd has been reconfigured to only accept SSL connections on port 5671, the
Pulp consumer configuration file (/etc/pulp/consumer/consumer.conf) needs to be edited.
The properties in the *messaging* section that specify the port, the CA certificate and
client certificate need to be updated as follows:

scheme
    The protocol used in the URL. (value: ssl)

port
    The port number. (value: 5671)

cacert
    The fully qualified path to the CA certificate used to validate the broker.
    (value: /etc/pki/pulp/qpid/ca.crt)

clientcert
    The fully qualified path a file containing both the client private key and certificate.
    (value: /etc/pki/pulp/qpid/client.crt)


Step #5 - Copy certificates to consumers
----------------------------------------

In step #4, we updated the consumer.conf and specified the SSL properties which included
the paths to the CA and client certificate files.  Those files need to be copied to each
consumer.

Eg:

::

 cd /etc/pki/pulp/qpid
 scp ca.crt root@<host>:/etc/pki/pulp/qpid
 scp client.crt root@<host>:/etc/pki/pulp/qpid

Note: the <host> is the hostname of a consumer.


Step #6 - Install qpid-cpp-server-ssl
-------------------------------------

To support SSL, the QPID broker must have the SSL module installed.  This module
is provided by the *qpid-cpp-server-ssl* package.  Make sure this package is installed.


Step #7 - Restart services
--------------------------

Now that the QPID and pulp configurations have been updated, the corresponding services
need to be restarted.  These services are:

  * qpidd
  * httpd
  * pulp-agent


Helpful Links
-------------

  * ​http://www.mail-archive.com/qpid-commits@incubator.apache.org/msg06212.html
  * ​http://www.mozilla.org/projects/security/pki/nss/tools/certutil.html
  ​* http://rajith.2rlabs.com/2010/03/01/apache-qpid-securing-connections-with-ssl/