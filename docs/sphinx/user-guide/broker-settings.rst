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

Pulp uses the message broker in two ways:

    * For Pulp Server <--> Pulp Consumer Agent communication such as a server initiated bind or
      update.

    * For Pulp Server <--> Pulp Worker asynchronous, server-side tasks such as syncing, publishing,
      or deletion of content.

Pulp Server settings are contained in ``/etc/pulp/server.conf`` and are located in two sections
corresponding with the two ways Pulp uses the message broker. The Pulp Server <--> Pulp Consumer
Agent communication settings are contained in the ``[messaging]`` section. The asynchronous task
settings are contained in the ``[tasks]`` section. Refer to the inline documentation of those
sections for more information on the options and their usage.

All settings in ``[tasks]`` and ``[messaging]`` have a default. If a setting is not specified
because it is either omitted or commented out, the default is used. The default values for each
option are shown but commented out in ``/etc/pulp/server.conf``.

Pulp Consumer Agent settings are contained in ``/etc/pulp/consumer/consumer.conf`` in the
``[messaging]`` section and define how the Consumer Agent connects to the broker to communicate
with the Pulp Server. The ``[messaging]`` section of ``/etc/pulp/consumer/consumer.conf`` on each
Pulp Consumer and the ``[messaging]`` section of ``/etc/pulp/server.conf`` on each Pulp Server need
to connect to the same broker for correct operation. The values and settings in
``/etc/pulp/consumer/consumer.conf`` correspond with the settings in ``/etc/pulp/server.conf``, but
uses a slightly different setting names. Refer to the inline documentation in the ``[messaging]``
section of ``/etc/pulp/consumer/consumer.conf`` for more information on how to configure the
settings of a consumer.

These two areas of Pulp can use the same message bus, or not. There is not a requirement that these
use the same broker.

To apply your changes after making any adjustment to ``/etc/pulp/server.conf``, you should restart
all Pulp services on any Pulp Server using the ``/etc/pulp/server.conf`` file edited. To apply your
changes made to a ``/etc/pulp/consumer/consumer.conf`` file, restart the Consumer Agent
(``goferd``) on any Consumer that uses that file. Normally each configuration file is kept
individually on each computer (Server or Consumer), and in those cases you only restart the
corresponding service on that specific machine. For more custom environments where config files are
shared between servers or consumers you may need to restart services on multiple computers.


Qpid on localhost (the default settings)
----------------------------------------

The default Pulp settings assume that both Pulp Server <--> Pulp Consumer Agent communication and
Pulp Server <--> Pulp Worker communication use Qpid on localhost at the default port (5672) without
SSL and without authentication. All settings in the ``[messaging]`` and ``[tasks]`` sections are
commented out by default, so the default values are used. The defaults are included in the
commented lines for clarity.
::

    [messaging]
    # url: tcp://localhost:5672
    # transport: qpid
    # auth_enabled: true
    # cacert: /etc/pki/qpid/ca/ca.crt
    # clientcert: /etc/pki/qpid/client/client.pem
    # topic_exchange: 'amq.topic'

    [tasks]
    # broker_url: qpid://guest@localhost/
    # celery_require_ssl: false
    # cacert: /etc/pki/pulp/qpid/ca.crt
    # keyfile: /etc/pki/pulp/qpid/client.crt
    # certfile: /etc/pki/pulp/qpid/client.crt

The default settings of a Pulp Consumer Agent are found in ``/etc/pulp/consumer/consumer.conf`` and
assume Qpid is running on localhost at the default port (5672) without SSL and without
authentication. In almost all installations, at a minimum, the ``host`` attributed will need to be
updated. The default configuration is shown below. If ``host`` in the ``[messaging]`` section is
blank, the ``host`` attribute in the ``[server]`` section of ``/etc/pulp/consumer/consumer.conf``
is used, which defaults to ``localhost.localdomain``.
::

    [messaging]
    scheme = tcp
    host =
    port = 5672
    transport = qpid
    cacert =
    clientcert =


Qpid on a Different Host
------------------------

To use Qpid on a different host for the Pulp Server <--> Pulp Consumer Agent communication, update
the ``url`` parameter in the ``[messaging]`` section. For example, if the hostname to connect to is
``someotherhost.com`` uncomment ``url`` and set it as follows:

    ``url: tcp://someotherhost.com:5672``

The ``/etc/pulp/consumer/consumer.conf`` file on each Pulp Consumer also needs to be updated to
correspond with this change. Refer to the inline documentation in
``/etc/pulp/consumer/consumer.conf`` to set the configuration correctly.

To use Qpid on a different host for Pulp Sever <--> Pulp Worker communication, update the
``broker_url`` parameter in the ``[tasks]`` section. For example, if the hostname to connect to is
``someotherhost.com`` uncomment ``broker_url`` and set it as follows:

    ``broker_url: qpid://guest@someotherhost.com/``


.. _pulp-broker-qpid-with-username-password:

Qpid with Username and Password Authentication
----------------------------------------------

The Pulp Server <--> Pulp Consumer Agent only support certificate based authentication, however the
Pulp Server <--> Pulp Worker communication does allow for username and password based auth.

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

To use Qpid with a non-standard port for Pulp Server <--> Pulp Consumer Agent communication, update
the ``url`` parameter in the ``[messaging]`` section. For example, if Qpid is listening on port
``9999``, uncomment ``url`` and set it as follows:

    ``url: tcp://localhost:9999``

The ``/etc/pulp/consumer/consumer.conf`` file on each Pulp Consumer also needs to be updated to
correspond with this change. Refer to the inline documentation in
``/etc/pulp/consumer/consumer.conf`` to set the configuration correctly.

To use Qpid with a non-standard port for Pulp Sever <--> Pulp Worker communication, update the
``broker_url`` parameter in the ``[tasks]`` section. For example, if Qpid is listening on port
``9999``, uncomment ``broker_url`` and set it as follows:

    ``broker_url: qpid://guest@localhost:9999/``


Qpid with SSL
-------------

SSL communication with Qpid is supported by both the Pulp Server <--> Pulp Consumer Agent and the
Pulp Server <--> Pulp Worker components. To use Pulp with Qpid using SSL, you'll need to configure
Qpid to accept SSL configuration. That configuration can be complex, so Pulp provides its own docs
and utilities to make configuring the Qpid with SSL easier. You can find those items in the
:ref:`Qpid SSL Configuration Guide <qpid-ssl-configuration>`.

After configuring the broker with SSL and generating certificates, you should have a CA
certificate, a client certificate, and a client certificate key. SSL with Qpid is by default on
port 5671, and this example assumes that.

To configure Pulp Server <--> Pulp Consumer Agent communication to connect to Qpid using SSL, uncomment
and set the following settings in the ``[messaging]`` section. The below configuration is an
example; update ``<host>`` in the ``url`` setting and the absolute path of the ``cacert`` and
``clientcert`` settings for your environment accordingly.
::

    [messaging]
    url: ssl://<host>:5671
    cacert: /etc/pki/pulp/qpid/ca.crt
    clientcert: /etc/pki/pulp/qpid/client.crt


The Pulp Server <--> Pulp Consumer Agent SSL configuration requires the client keyfile and client
certificate to be stored in the same file.

The ``/etc/pulp/consumer/consumer.conf`` file on each Pulp Consumer also needs to be updated to
correspond with this change. Refer to the inline documentation in
``/etc/pulp/consumer/consumer.conf`` to set the configuration correctly.

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


The Pulp Server <--> Pulp Worker communication allows the client key and client certificate to be
stored in the same or different files. If the key and certificate are in the same file, set the
same absolute path for both ``keyfile`` and ``certfile``.


Using Pulp with RabbitMQ
------------------------
Pulp Server <--> Pulp Consumer Agent and Pulp Server <--> Pulp Worker communication should both
work with RabbitMQ, although it does not receive the same amount of testing by Pulp developers.

For a Pulp Server or Pulp Consumer Agent to use RabbitMQ, you'll need to install the
``python-gofer-amqplib`` package on each Server or Consumer. This can be done by running:

    ``sudo yum install python-gofer-amqplib``

Enable RabbitMQ support for Pulp Server <--> Pulp Consumer Agent communication by
uncommenting and updating the ``transport`` setting in ``[messaging]`` to ``rabbitmq``. Below is an
example:

    ``transport: rabbitmq``

The ``/etc/pulp/consumer/consumer.conf`` file on each Pulp Consumer also needs to be updated to
correspond with this change. Refer to the inline documentation in
``/etc/pulp/consumer/consumer.conf`` to set the configuration correctly.

Enable RabbitMQ support for Pulp Server <--> Pulp Worker communication by uncommenting and updating
the ``broker_url`` broker string to use the protocol handler ``amqp://``. Below is an example:

    ``broker_url: amqp://guest:guest@localhost//``


RabbitMQ with a Specific vhost
------------------------------

RabbitMQ supports an isolation feature called vhosts. These can be used by appending them to the
broker string after the forward slash following the hostname. The default vhost in RabbitMQ is a
forward slash, causing the broker string to sometimes be written with an additional slash. This
form is for clarity as the the default vhost is assumed if none is specified.

Pulp Server <--> Pulp Consumer Agent communication through RabbitMQ on a vhost is not supported.

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

The ``/etc/pulp/consumer/consumer.conf`` file on each Pulp Consumer also needs to be updated to
correspond with this change. Refer to the inline documentation in
``/etc/pulp/consumer/consumer.conf`` to set the configuration correctly.

