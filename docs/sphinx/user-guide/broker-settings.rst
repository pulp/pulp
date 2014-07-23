:orphan:

.. _pulp-broker-settings:

Pulp Broker Settings
====================

Pulp requires a message bus to run and can use either Qpid or RabbitMQ as that message bus. Pulp
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

    * For Pulp server <--> Pulp consumer communication such as a server initiated bind, or update.
    * For Pulp server <--> Pulp workers asynchronous, server-side tasks such as syncing, publishing,
      or deletion of content.

Pulp broker settings are contained in ``/etc/pulp/server.conf`` and are located in two sections
corresponding with the two ways Pulp uses the message broker. The Pulp server <--> Pulp consumer
communication settings are contained in the ``[messaging]`` section. The asynchronous task settings
are contained in the ``[tasks]`` section.

All settings in ``[tasks]`` and ``[messaging]`` have a default. If a setting is not specified
because it is either omitted or commented out, the default is used. See the sections below for an
explanation of each setting and its default.

These two areas of Pulp can use the same message bus, or not. There is not a requirement that these
use the same broker.

To apply your changes after making any adjustment to ``/etc/pulp/server.conf``, you should restart
all Pulp services.


[messaging] Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^

The following settings are used by Pulp server and Pulp consumer to communicate through the message
bus. These are defined in the ``[messaging]`` section of ``/etc/pulp/server.conf``.

url
    The broker string that should be used by Pulp servers and Pulp consumers to connect to the
    message bus. The default is ``tcp://localhost:5672``. Use ``tcp://`` as the protocol handler for
    non-SSL connection, and ``ssl://`` for SSL connections.

transport
    The type of message broker being used. The default is ``qpid``, which assumes the broker type is
    Qpid. For RabbitMQ, ``rabbitmq`` should be used.

auth_enabled
    Identifies if gofer will use authentication. The default is ``true``, which enables certificate
    based authentication. To disable authentication, use ``false``.

cacert
    The absolute path to the PEM encoded CA Certificate to be used by gofer. The default is
    ``/etc/pki/qpid/ca/ca.crt``. This is used to validate the identity of the broker.

clientcert
    The absolute path to the PEM encoded certificate a message bus client will present to the
    broker to prove its client identity. The default is ``/etc/pki/qpid/client/client.pem``

topic_exchange
    The AMQP topic exchange gofer will use for communication. The default is ``'amq.topic'``
    (includes single quotes).


[tasks] Configuration
^^^^^^^^^^^^^^^^^^^^^

The following settings are used by Pulp server and Pulp workers to communicate through the message
bus to perform asynchronous, server-side task work such as syncing, publishing, or deletion of
content. These are defined in the ``[tasks]`` section of ``/etc/pulp/server.conf``.

broker_url
    The broker string that should be used by Pulp server and Pulp workers to connect to the message
    bus. The default is ``qpid://guest@localhost/``. Use ``qpid://`` as protocol handler when
    connecting to a Qpid broker, and use ``amqp://`` when connecting to a RabbitMQ broker.
    Username, password, and port syntax is supported using standard URL syntax for both brokers.

celery_require_ssl
    Require SSL if set to ``true``, otherwise do not require SSL. The default is ``false``.

cacert
    The absolute path to the PEM encoded CA Certificate allowing identity validation of the message
    bus. The default is ``/etc/pki/pulp/qpid/ca.crt``.

keyfile
    The absolute path to the keyfile used for authentication to the message bus. This is the
    private key that corresponds with the certificate. The default value is
    ``/etc/pki/pulp/qpid/client.crt``. Sometimes keys are kept in the same file as the certificate
    itself, and the default assumes that is the case.

certfile
    The absolute path to the PEM encoded certificate used for authentication to the message bus.
    The default value is ``/etc/pki/pulp/qpid/client.crt``.


Qpid on localhost (the default settings)
----------------------------------------

The default Pulp settings assume that both Pulp Server <--> Pulp Consumer communication and Pulp
Server <--> Pulp Worker communication use Qpid on localhost at the default port (5672) without SSL
and without authentication. All settings in the ``[messaging]`` and ``[tasks]`` sections are
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


Qpid on a Different Host
------------------------

To use Qpid on a different host for the Pulp Server <--> Pulp Consumer communication, update the
``url`` parameter in the ``[messaging]`` section. For example, if the hostname to connect to is
``someotherhost.com`` uncomment ``url`` and set it as follows:

    ``url: tcp://someotherhost.com:5672``

To use Qpid on a different host for Pulp Sever <--> Pulp Worker communication, update the
``broker_url`` parameter in the ``[tasks]`` section. For example, if the hostname to connect to is
``someotherhost.com`` uncomment ``broker_url`` and set it as follows:

    ``broker_url: qpid://guest@someotherhost.com/``


Qpid with Username and Password Authentication
----------------------------------------------

The Pulp Server <--> Pulp Consumer only support certificate based authentication, however the Pulp
Server <--> Pulp Worker communication does allow for username and password based auth.

To use Pulp with Qpid and username and password authentication, you'll need to configure the
usernames and passwords on the Qpid broker, and then configure Pulp. Refer to the Qpid
documentation for how to configure the broker. This section explains how to configure Pulp to use a
username and password configured in Qpid.

Assuming Qpid has the user ``foo`` and the password ``bar`` configured, enable Pulp to use them by
uncommenting the ``broker_url`` setting in ``[tasks]`` and setting it as follows:

    ``broker_url: qpid://foo:bar@localhost.com/``


Qpid on a Non-Standard Port
---------------------------

To use Qpid with a non-standard port for Pulp Server <--> Pulp Consumer communication, update the
``url`` parameter in the ``[messaging]`` section. For example, if Qpid is listening on port
``9999``, uncomment ``url`` and set it as follows:

    ``url: tcp://localhost:9999``

To use Qpid with a non-standard port for Pulp Sever <--> Pulp Worker communication, update the
``broker_url`` parameter in the ``[tasks]`` section. For example, if Qpid is listening on port
``9999``, uncomment ``broker_url`` and set it as follows:

    ``broker_url: qpid://guest@localhost:9999/``


Qpid with SSL
-------------

SSL communication with Qpid is supported by both the Pulp Server <--> Pulp Consumer and the Pulp
Server <--> Pulp Worker components. To use Pulp with Qpid using SSL, you'll need to configure Qpid
to accept SSL configuration. That configuration can be complex, so Pulp provides its own docs and
utilities to make configuring the Qpid with SSL easier. You can find those items in the
:ref:`Qpid SSL Configuration Guide <qpid-ssl-configuration>`.

After configuring the broker with SSL and generating certificates, you should have a CA
certificate, a client certificate, and a client certificate key. SSL with Qpid is by default on
port 5671, and this example assumes that.

To configure Pulp Server <--> Pulp Consumer communication to connect to Qpid using SSL, uncomment
and set the following settings in the ``[messaging]`` section. The below configuration is an
example; update ``<host>`` in the ``url`` setting and the absolute path of the ``cacert`` and
``clientcert`` settings for your environment accordingly.
::

    [messaging]
    url: ssl://<host>:5671
    cacert: /etc/pki/pulp/qpid/ca.crt
    clientcert: /etc/pki/pulp/qpid/client.crt

The Pulp Server <--> Pulp Consumer SSL configuration requires the client keyfile and client
certificate to be stored in the same file.

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
Pulp Server <--> Pulp Consumer and Pulp Server <--> Pulp Worker communication should both work with
RabbitMQ, although it does not receive the same amount of testing by Pulp developers.

For either section of Pulp to use RabbitMQ, you'll need to install the ``python-gofer-amqplib``
package. This can be done by running:

    ``sudo yum install python-gofer-amqplib``

Enable RabbitMQ support for Pulp Server <--> Pulp Consumer communication by
uncommenting and updating the ``transport`` setting in ``[messaging]`` to ``rabbitmq``. Below is an
example:

    ``transport: rabbitmq``

Enable RabbitMQ support for Pulp Server <--> Pulp Worker communication by uncommenting and updating
the ``broker_url`` broker string to use the protocol handler ``amqp://``. Below is an example:

    ``broker_url: amqp://guest:guest@localhost//``


RabbitMQ with a Specific vhost
------------------------------

RabbitMQ supports an isolation feature called vhosts. These can be used by appending them to the
broker string after the forward slash following the hostname. The default vhost in RabbitMQ is a
forward slash, causing the broker string to sometimes be written with an additional slash. This
form is for clarity as the the default vhost is assumed if none is specified.

To enable Pulp Server <--> Pulp Consumer communication through RabbitMQ on a vhost, uncomment and
update the ``url`` setting in ``[messaging]`` to include the vhost at the end. For example, if the
vhost is 'foo' with the rest of the settings as defaults, the following example will work:

    ``url: tcp://localhost:5672/foo``

To enable Pulp Server <--> Pulp Worker communication through RabbitMQ on a vhost, uncomment and
update the ``broker_url`` setting in ``[tasks]`` to include the vhost at the end. For example, if
the vhost is 'foo' with the rest of the settings as defaults, the following example will work:

    ``broker_url: amqp://guest:guest@localhost/foo``


RabbitMQ with SSL
-----------------
RabbitMQ with SSL support is configured the same as it is with Qpid with the only difference being
the adjustment to the ``transport`` setting in ``[messaging]`` and the protocol handler of
``broker_url`` in ``[tasks]``.
