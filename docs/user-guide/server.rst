Server
======

Conflicting Operations
----------------------

Pulp, by its nature, is a highly concurrent application. Operations such
as a repository sync or publish could conflict with each other if run against
the same repository at the same time. For any such operation where it is important
that a resource be effectively "locked", pulp will create a task object and put
it into a queue. Pulp then guarantees that as workers take tasks off the queue,
only one task will execute at a time for any given resource.

Recovery from Worker Failure
----------------------------

If a worker dies unexpectedly, the dispatched Pulp tasks destined for that worker will stall for
at most six minutes before being cancelled. A monitoring component inside of pulp_celerybeat
monitors all workers using heartbeats. If a worker does not heartbeat within five minutes, it is
considered missing. This check occurs once a minute, causing a maximum delay of six minutes
before a worker is considered missing by Pulp.

A missing worker has all tasks destined for it cancelled, and no new work is assigned to the
missing worker. This causes new Pulp operations dispatched to continue normally with the other
available workers. If a worker with the same name is started again after being missing, it is
added into the pool of workers as any worker starting up normally would.

Backups
-------

A complete backup of a pulp server includes:

- ``/var/lib/pulp`` a full copy of the filesystem
- ``/etc/pulp`` a full copy of the filesystem
- ``/etc/pki/pulp`` a full copy of the filesystem
- any custom Apache configuration
- `MongoDB`: a full backup of the database and configuration
- `Qpid` or `RabbitMQ`: a full backup of the durable queues and configuration

To do a complete restoration:

#. Install pulp and restore ``/etc/pulp`` and ``/etc/pki/pulp``
#. Restore ``/var/lib/pulp``
#. Restore the message broker service. If you cannot restore the state of the
   broker's durable queues, then first run ``pulp-manage-db`` against an empty
   database. Pulp will perform all initialization operations, including creation
   of required queues. Then drop the database before moving on.
#. Restore the database
#. Start all of the pulp services
#. Cancel any tasks that are not in a final state

.. _server-components:

Components
----------

Pulp server has several components that can be restarted individually if the need arises.
Each has a description below.  See the :ref:`services` section in this guide for more information
on restarting services.

Apache
^^^^^^

This component is responsible for the REST API.

The service name is ``httpd``.

Workers
^^^^^^^

This component is responsible for performing asynchronous tasks, such as sync
and publish.

The service name is ``pulp_workers``.

Celery Beat
^^^^^^^^^^^

This is a singleton (there must only be one celery beat process per pulp deployment)
that is responsible for queueing scheduled tasks. It also plays a role in
monitoring the availability of workers.

The service name is ``pulp_celerybeat``.


Resource Manager
^^^^^^^^^^^^^^^^

This is a singleton (there must only be one of these worker processes per pulp
deployment) celery worker that is responsible for assigning tasks to
other workers based on which resource they need to reserve. When you see log
messages about tasks that reserve and release resources, this is the worker that
performs those tasks.

The service name is ``pulp_resource_manager``.

Configuration
-------------

This section contains documentation on the configuration of the various Pulp Server components.

httpd
^^^^^

.. _crl-support:

CRL Support
~~~~~~~~~~~

Pulp used to support Certificate Revocation Lists in versions up to and including 2.4.0. Starting
with 2.4.1, the Pulp team decided not to carry their own M2Crypto build which had the patches
necessary to perform CRL checks. Instead, users can configure httpd to do this using its
SSLCARevocationFile and SSLCARevocationPath directives. See the `mod-ssl documentation`_ for more
information.

.. _mod-ssl documentation: https://httpd.apache.org/docs/2.2/mod/mod_ssl.html

Plugins
^^^^^^^

Many Pulp plugins support these settings in their config files. Rather than documenting these
settings in each project repeatedly, the commonly accepted key-value pairs are documented below.

Importers
~~~~~~~~~

Most of Pulp's importers support these key-value settings in their config files:

``proxy_url``: A string in the form of scheme://host, where scheme is either ``http`` or ``https``

``proxy_port``: An integer representing the port number to use when connecting to the proxy server

``proxy_username``: If provided, Pulp will attempt to use basic auth with the proxy server using this
as the username

``proxy_password``: If provided, Pulp will attempt to use basic auth with the proxy server using this
as the password
