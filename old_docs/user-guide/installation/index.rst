Installation
============

Pulp operates with three main components that get installed potentially on different
machines.

Server
  This is the main application server that stores data and distributes content.

Client
  This is a command line component that comes as two pieces: admin-client,
  which manages the server; and consumer-client, which manages a consumer's relationship
  to the server. admin-client can be run from any machine that can access the server's
  REST API, but the consumer-client must be run on a consumer.

Additional steps are needed for upgrading Pulp 1.1 installations. More information can be found
in the :doc:`v1_upgrade` section of this guide.

The :ref:`platform-support-policy` defines platforms are currently supported.


Prerequisites
-------------

* The following ports must be open into the server:

 * 80 for consumers to access repositories served over HTTP
 * 443 for consumers to access repositories served over HTTPS
 * 443 for clients (both admin and consumer) to access Pulp APIs
 * 5671 for consumers to connect to the message bus if it is running over TLS
 * 5672 for consumers to connect to the message bus if it is left unsecured

* The mod_python Apache module must be uninstalled or not loaded. Pulp uses
  mod_wsgi which conflicts with mod_python and will cause the server to fail.

.. warning::
  MongoDB is known to have
  `serious limitations <http://docs.mongodb.org/manual/faq/fundamentals/#what-are-the-32-bit-limitations>`_
  on 32-bit architectures. It is strongly advised that you run MongoDB on a 64-bit architecture.


Message Broker
^^^^^^^^^^^^^^

Qpid is the default message broker for Pulp, and is the broker used in this guide.

See the `Qpid packaging docs <http://qpid.apache.org/packages.html>`_ for information on
where to get Qpid packages for your OS.

If you would like to use RabbitMQ instead, see the
`RabbitMQ installation docs <http://www.rabbitmq.com/download.html>`_.


Storage Requirements
--------------------

MongoDB
^^^^^^^

The MongoDB database can easily grow to 10GB or more in size, which vastly
exceeds the amount of data actually stored in the database. This is normal
(but admittedly surprising) behavior for MongoDB. As such, make sure you
allocate plenty of storage within ``/var/lib/mongodb``.


Pulp
^^^^

Pulp stores its content in ``/var/lib/pulp``. The size requirements of this
directory vary depending on how much content you wish to download.

.. note::
   Making ``/var/lib/pulp`` a symbolic link to a different directory is possible,
   but it is recommended that you use a bind mount instead. As of Pulp 2.8.0, using
   a symbolic link requires you modify an Apache configuration. This configuration
   is found by default in ``/etc/httpd/conf.d/pulp_content.conf``. In the
   ``<Location /pulp/content/>`` section, you will need to add an entry for the target
   of your symbolic link. For example, if you have ``/var/lib/pulp`` point to
   ``/mnt/pulp``, you should add ``XSendFilePath`` entries for each directory you would
   like Apache to be able to serve from. If you fail to make this configuration change,
   you will receive an ``HTTP 403: Forbidden`` for all requests.


Instructions
------------

Please refer to the instructions below for your operating system.

.. toctree::
   :maxdepth: 2

   f23-
   f24+
