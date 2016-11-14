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

Failure and Recovery
--------------------

For a recap of Pulp components and the work they are responsible for, read :ref:`components <server-components>`.

* If a ``pulp_worker`` dies, the dispatched Pulp tasks destined for that worker (both the task
  currently being worked on and queued/related tasks) will not be processed. They will stall for
  at most six minutes before being canceled. Status of the tasks is marked as canceled after
  5 minutes or in case the worker has been re-started, whichever action occurs first.
  Cancellation after 5 minutes is dependent on ``pulp_celerybeat`` service running. A monitoring
  component inside of ``pulp_celerybeat`` monitors all workers' heartbeats. If a worker does not
  heartbeat within five minutes, it is considered missing. This check occurs once a minute, causing
  a maximum delay of six minutes before a worker is considered missing and tasks canceled by Pulp.

  A missing worker has all tasks destined for it canceled, and no new work is assigned to the
  missing worker. This causes new Pulp operations dispatched to continue normally with the other
  available workers. If a worker with the same name is started again after being missing, it is
  added into the pool of workers as any worker starting up normally would.

* If all instances of ``pulp_celerybeat`` die and new workers start, they won't
  be given work or if existing workers stop, Pulp will continue assigning them work incorrectly.
  Once restarted, ``pulp_celerybeat`` will synchronize with the current state of all workers.
  Scheduled tasks will not run if there are no ``pulp_celerybeat`` processes running, but
  they will run when the first ``pulp_celerybeat`` process is restarted.

* If ``pulp_resource_manager`` dies, the Pulp tasking system will halt. Once restarted it will
  resume.

* If the webserver dies the API will become unavailable until it is restored.

.. note::

    From Pulp 2.6.0 and further, the /status/ url will show the currenct status of Pulp components.
    Read more about it here :ref:`status API <getting_the_server_status>`, which includes sample
    response output.

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

This process is responsible for queueing scheduled tasks and is responsible for
monitoring the availability of workers. For fault tolerance, there can be multiple
instances of this process running. If one of them fails, another will take over.

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

.. _importer_settings:

Importers
~~~~~~~~~

Most of Pulp's importers support these key-value settings in their config files:

``proxy_url``: A string in the form of scheme://host, where scheme is either ``http`` or ``https``

``proxy_port``: An integer representing the port number to use when connecting to the proxy server

``proxy_username``: If provided, Pulp will attempt to use basic auth with the proxy server using this
as the username

``proxy_password``: If provided, Pulp will attempt to use basic auth with the proxy server using this
as the password
