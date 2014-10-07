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
