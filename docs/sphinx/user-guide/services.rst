Services
========


Server
------

Pulp server has several services that can be restarted individually if the
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


Consumer
--------

Pulp consumers can run an optional agent to support platform related remote operations.

Agent
^^^^^

The Pulp Agent runs as a plugin within the ``goferd`` service.

::

  $ sudo service goferd restart   # if you use upstart
  $ sudo systemctl restart goferd # if you use systemd

