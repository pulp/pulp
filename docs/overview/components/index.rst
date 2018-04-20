.. _RabbitMQ Clustering Guide: https://www.rabbitmq.com/clustering.html

Architecture and Scaling
========================

Pulp's architecture has five components to it. Each of these can be horizontally scaled
independently for both high availability and/or additional capacity for that part of the
architecture.

WSGI application
  Pulp's web application is served by one or more WSGI webservers. See the
  :ref:`wsgi-application` docs for more info on deploying and scaling this component.

Workers
  Pulp's tasking system requires at least one running worker. Additional workers can be added to add
  capacity to the tasking system.

Resource Manager
  Pulp's tasking system requires at least one running resource manager. Although it's required for
  correctness, it is almost always idle even in very large Pulp environments. As such, additional
  scaling may increase availability but will not increase tasking system throughput.

SQL Database
  Refer to the database documentation on how to scale it and/or make it highly available.

RabbitMQ
  Refer to the `RabbitMQ Clustering Guide`_ on how to cluster and scale RabbitMQ.


.. toctree::
   :maxdepth: 3

   webserver
