Broker Configuration
====================

Pulp requires a message bus to run, and can use either Qpid or RabbitMQ as that message bus. Pulp
is developed and tested against the Qpid C++ server v0.22+, and is configured to expect Qpid on
localhost without SSL or authentication by default. This documentation identifies changes necessary
for the following configurations:

   * Pulp Broker Settings Overview
   * Configure Pulp to use Qpid on a different host
   * Configure Pulp to use Qpid with SSL
   * Configure Pulp to use RabbitMQ without SSL
   * Configure Pulp to use RabbitMQ with SSL

Pulp Broker Settings Overview
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Pulp uses the message broker in two ways:

    * To perform asynchronous server-side tasks such as syncing, publishing, or deletion of content.
    * For Pulp server <--> Pulp consumer communication such as a server initiated bind, or update.

Pulp broker settings are contained in ``/etc/pulp/server.conf``, and are located in two sections
corresponding with the two ways Pulp uses the message broker. The Pulp server <--> Pulp consumer
communication settings are contained in the ``[messaging]`` section. The asynchronous task settings
are contained in the ``[tasks]`` section.

===Server and Consumer Communication===

===Server-side Tasks===

Qpid on localhost (the default settings)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Qpid on a different host
^^^^^^^^^^^^^^^^^^^^^^^^

Qpid with SSL
^^^^^^^^^^^^^

RabbitMQ without SSL
^^^^^^^^^^^^^^^^^^^^

RabbitMQ with SSL
^^^^^^^^^^^^^^^^^
