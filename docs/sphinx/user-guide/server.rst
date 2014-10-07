Server
======

Conflicting Operations
----------------------

Pulp, by its nature, is a highly concurrent application. Everything from the
client and APIs themselves down to the need to allow long running sync processes
to execute in the background lends itself to situations where conflicting
user requests may arise.

The simplest example is a situation where a user attempts to delete a repository
in the process of being synchronized. It is the responsibility of the server
to detect these sorts of situations and preserve the integrity of its data.

The Pulp server employs a coordination layer for this purpose. The majority
of the calls made against the server are first checked to verify their ability
to run. This test will result in one of three situations:

* In many cases, the call will be queued to run at the server's earliest convenience
  (factoring in overall server load).
* If a resource is currently busy, the call may be *postponed* until the resource
  becomes available. For example, if a repository configuration update is requested
  while the repository is performing a sync, the update call will be accepted by
  the server but will not execute until the sync completes.
* In rare cases, the call may be outright *rejected* if the resource is in a state
  where the call will never execute. For example, if a call to delete a repository
  is in the queue and a call is made after that to update its configuration, the
  update call will be rejected due to the fact that the repository will be
  deleted before the update call has a chance to resolve.

The client will indicate which of the three possibilities occurred and provides
commands to work with tasks for a given resource (for instance,
the :ref:`repository tasks <repo-tasks>` series of commands).

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

Components
----------

Pulp server has several components that can be restarted individually if the
need arises. Each has a description below along with an example of how to
restart.

Apache
^^^^^^

This component is responsible for the REST API.

::

  $ sudo service httpd restart   # if you use upstart
  $ sudo systemctl restart httpd # if you use systemd

Workers
^^^^^^^

This component is responsible for performing asynchronous tasks, such as sync
and publish.

::

  $ sudo service pulp_workers restart   # if you use upstart
  $ sudo systemctl restart pulp_workers # if you use systemd

Celery Beat
^^^^^^^^^^^

This is a singleton (there must only be one celery beat process per pulp deployment)
that is responsible for queueing scheduled tasks. It also plays a role in
monitoring the availability of workers.

::

  $ sudo service pulp_celerybeat restart   # if you use upstart
  $ sudo systemctl restart pulp_celerybeat # if you use systemd

Resource Manager
^^^^^^^^^^^^^^^^

This is a singleton (there must only be one of these worker processes per pulp
deployment) celery worker that is responsible for assigning tasks to
other workers based on which resource they need to reserve. When you see log
messages about tasks that reserve and release resources, this is the worker that
performs those tasks.

::

  $ sudo service pulp_resource_manager restart   # if you use upstart
  $ sudo systemctl restart pulp_resource_manager # if you use systemd

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
