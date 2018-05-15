.. _rq: http://python-rq.org

Architecture and Scaling
========================

Pulp's architecture has three components to it. Each of these can be horizontally scaled
independently for both high availability and/or additional capacity for that part of the
architecture.

WSGI application
  Pulp's web application is served by one or more WSGI webservers. See the
  :ref:`wsgi-application` docs for more info on deploying and scaling this component.

Queue
  Pulp's tasking system requires running `rq`_. Additional rq workers can be added to add
  capacity to the tasking system.

SQL Database
  Refer to the database documentation on how to scale it and/or make it highly available.


.. toctree::
   :maxdepth: 3

   webserver
