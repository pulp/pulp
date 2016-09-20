:orphan:

.. _pulp-broker-settings:

Pulp Broker Settings
====================

Pulp requires a message bus to run. Either Qpid or RabbitMQ can be used as that message bus. Pulp
is developed and tested against the Qpid C++ server v0.22+ and is configured to expect Qpid on
localhost without SSL or authentication by default. This documentation identifies changes necessary
for the following configurations:

   * Pulp Broker Settings Overview
   * Configure Pulp to use Qpid on a different host
   * Configure Pulp to use Qpid with SSL
   * Configure Pulp to use RabbitMQ without SSL
   * Configure Pulp to use RabbitMQ with SSL


Pulp Broker Settings Overview
-----------------------------

Pulp uses the message broker:

    * For Pulp Server <--> Pulp Worker asynchronous, server-side tasks such as syncing, publishing,
      or deletion of content.

Pulp Server settings are contained in ``/etc/pulp/server.conf`` and are located in two sections
corresponding with the two ways Pulp uses the message broker. The Pulp Server <--> Pulp Consumer.
The asynchronous task settings are contained in the ``[tasks]`` section. Refer to the inline
documentation of those sections for more information on the options and their usage.

All settings in ``[tasks]`` have a default. If a setting is not specified
because it is either omitted or commented out, the default is used. The default values for each
option are shown but commented out in ``/etc/pulp/server.conf``.

To apply your changes after making any adjustment to ``/etc/pulp/server.conf``, you should restart
all Pulp services on any Pulp Server using the ``/etc/pulp/server.conf`` file edited.
Normally each configuration file is kept individually on each computer (Server or Consumer),
and in those cases you only restart the corresponding service on that specific machine.
For more custom environments where config files are shared between servers or consumers you
may need to restart services on multiple computers.


Qpid on localhost (the default settings)
----------------------------------------

The default Pulp settings assume that
Pulp Server <--> Pulp Worker communication use Qpid on localhost at the default port (5672) without
SSL and without authentication. All settings in the ``[messaging]`` and ``[tasks]`` sections are
commented out by default, so the default values are used. The defaults are included in the
commented lines for clarity.
::

    [tasks]
    # broker_url: qpid://guest@localhost/
    # celery_require_ssl: false
    # cacert: /etc/pki/pulp/qpid/ca.crt
    # keyfile: /etc/pki/pulp/qpid/client.crt
    # certfile: /etc/pki/pulp/qpid/client.crt
    # login_method:

Qpid on a Different Host
------------------------

The ``/etc/pulp/consumer/consumer.conf`` file on each Pulp Consumer needs to be updated to
correspond with this change. Refer to the inline documentation in
``/etc/pulp/consumer/consumer.conf`` to set the configuration correctly.

To use Qpid on a different host for Pulp Sever <--> Pulp Worker communication, update the
``broker_url`` parameter in the ``[tasks]`` section. For example, if the hostname to connect to is
``someotherhost.com`` uncomment ``broker_url`` and set it as follows:

    ``broker_url: qpid://guest@someotherhost.com/``


.. _pulp-broker-qpid-with-username-password:

Qpid with Username and Password Authentication
----------------------------------------------

The Pulp Server <--> Pulp Worker communication does allow certificate based authentication
for username and password based auth.

Pulp can authenticate using a username and password with Qpid using SASL. Refer to the Qpid docs
on how to configure Qpid for SASL, but here are a few helpful pointers:

1. Ensure the Qpid machine has the ``cyrus-sasl-plain`` package installed. After installing it,
   restart Qpid to ensure it has taken effect.

2. Configure the username and password in the SASL database. Refer to Qpid docs for the specifics
   of this.

3. Ensure the qpidd user has read access to the SASL database.

After configuring the broker for SASL, then configure Pulp. This section explains how to configure
Pulp to use a username and password configured in Qpid.

Assuming Qpid has the user ``foo`` and the password ``bar`` configured, enable Pulp to use them by
uncommenting the ``broker_url`` setting in ``[tasks]`` and setting it as follows:

    ``broker_url: qpid://foo:bar@localhost.com/``


Qpid on a Non-Standard Port
---------------------------

To use Qpid with a non-standard port for Pulp Sever <--> Pulp Worker communication, update the
``broker_url`` parameter in the ``[tasks]`` section. For example, if Qpid is listening on port
``9999``, uncomment ``broker_url`` and set it as follows:

    ``broker_url: qpid://guest@localhost:9999/``


Qpid with SSL
-------------

SSL communication with Qpid is supported by the
Pulp Server <--> Pulp Worker components. To use Pulp with Qpid using SSL, you'll need to configure
Qpid to accept SSL configuration. That configuration can be complex, so Pulp provides its own docs
and utilities to make configuring the Qpid with SSL easier. You can find those items in the
:ref:`Qpid SSL Configuration Guide <qpid-ssl-configuration>`.

After configuring the broker with SSL and generating certificates, you should have a CA
certificate, a client certificate, and a client certificate key. SSL with Qpid is by default on
port 5671, and this example assumes that.

To configure Pulp Server <--> Pulp Worker communication to connect to Qpid using SSL, uncomment and
set the following settings in the ``[messaging]`` section. The below configuration is an example;
update ``<host>`` in the ``broker_url`` setting and the absolute path of the ``cacert``,
``keyfile``, and ``certfile`` settings for your environment accordingly.
::

    [tasks]
    broker_url: qpid://<host>:5671/
    celery_require_ssl: true
    cacert: /etc/pki/pulp/qpid/ca.crt
    keyfile: /etc/pki/pulp/qpid/client.crt
    certfile: /etc/pki/pulp/qpid/client.crt
    # login_method:


The Pulp Server <--> Pulp Worker communication allows the client key and client certificate to be
stored in the same or different files. If the key and certificate are in the same file, set the
same absolute path for both ``keyfile`` and ``certfile``.

.. note::

     If your Qpid broker requires authentication with ``auth=yes`` and requires SSL client
     authentication with ``ssl-require-client-authentication=yes`` then you may want to have Pulp
     authenticate using the ``EXTERNAL`` method. To configure this you will need to:

          1. Set ``login_method`` to ``EXTERNAL``

          2. Ensure that the broker string contains a username that is identical to the ``CN``
             contained in the client certificate specified in the ``certfile`` setting of the
             ``[tasks]`` section.

     For example, if the ``cacert`` has ``CN=mypulpuser`` and connects to ``example.com`` on port
     5671, then ``broker_url`` should be set to:

          broker_url: qpid://mypulpuser@example.com:5671/


Using Pulp with RabbitMQ
------------------------
Pulp Server <--> Pulp Worker communication should
work with RabbitMQ, although it does not receive the same amount of testing by Pulp developers.

For a Pulp Server to use RabbitMQ, you'll need to install the
``python-gofer-amqp`` package on each Server or Consumer. This can be done by running:

    ``sudo yum install python-gofer-amqp``

Enable RabbitMQ support for Pulp Server <--> Pulp Worker communication by uncommenting and updating
the ``broker_url`` broker string to use the protocol handler ``amqp://``. Below is an example:

    ``broker_url: amqp://guest:guest@localhost//``


RabbitMQ with a Specific vhost
------------------------------

RabbitMQ supports an isolation feature called vhosts. These can be used by appending them to the
broker string after the forward slash following the hostname. The default vhost in RabbitMQ is a
forward slash, causing the broker string to sometimes be written with an additional slash. This
form is for clarity as the the default vhost is assumed if none is specified.

To enable Pulp Server <--> Pulp Worker communication through RabbitMQ on a vhost, uncomment and
update the ``broker_url`` setting in ``[tasks]`` to include the vhost at the end. For example, if
the vhost is 'foo' with the rest of the settings as defaults, the following example will work:

    ``broker_url: amqp://guest:guest@localhost/foo``


RabbitMQ with SSL
-----------------
RabbitMQ with SSL support is configured the same as it is with Qpid with the only difference being
the adjustment to the ``transport`` setting in ``[messaging]`` and the protocol handler of
``broker_url`` in ``[tasks]``. Both of these sections are contained on the Pulp Server in
``/etc/pulp/server.conf``.

If RabbitMQ is using strict SSL client certificate checking, you will need to set ``login_method``
to ``EXTERNAL``. See :redmine:`1168` for more details.

The ``/etc/pulp/consumer/consumer.conf`` file on each Pulp Consumer also needs to be updated to
correspond with this change. Refer to the inline documentation in
``/etc/pulp/consumer/consumer.conf`` to set the configuration correctly.
