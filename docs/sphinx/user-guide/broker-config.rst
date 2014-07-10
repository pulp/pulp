Broker Configuration
====================

Pulp requires a message bus to run, and can use either Qpid or RabbitMQ as that message bus. Pulp
is developed and tested against C++ Qpid server v0.22+, and is configured to expect Qpid on
localhost by default. This documentation identifies the following things:

   * Which settings cause Pulp to expect Qpid on localhost as the default broker
   * Configure Pulp to use Qpid on a different host
   * Configure Pulp to use Qpid with SSL
   * Configure Pulp to use RabbitMQ without SSL
   * Configure Pulp to use RabbitMQ with SSL

Overview
^^^^^^^^
Successfully 

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
