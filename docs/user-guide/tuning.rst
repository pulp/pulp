Tuning and Scaling
==================

Tuning
------

WSGI Processes
^^^^^^^^^^^^^^

By default, each Apache server on which pulp is deployed will start 3 WSGI processes to
serve the REST API. The number of processes can be adjusted in
``/etc/httpd/conf.d/pulp.conf`` on the ``WSGIDaemonProcess`` statement, along
with other items. See the Apache documentation of ``mod_wsgi`` for details.

For tuning purposes, consider pulp's REST API to be a low-traffic web
application that has occasional spikes in memory use when returning large data
sets. Most of pulp's heavy-lifting has been offloaded to celery workers.


Scaling
-------

Great effort has been put into Pulp 2.4 to make it less monolithic and more
scalable. A default Pulp install is an "all-in-one" style setup with everything
running on one machine. However, the components of Pulp can be moved to
different servers or containers to increase availability and performance.

Overview of Pulp components
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pulp consists of a number of components:

* ``httpd`` - on a "all-in-one" install, this serves published repos and
  processes REST API requests. Short tasks like repository creation are handled
  immediately whereas longer tasks are queued up for processing by a worker.

* ``pulp_workers`` - Worker processes handle longer running tasks like
  repository publishes and syncs. In an "all-in-one" install, there is one worker
  per CPU core by default.

* ``pulp_celerybeat`` - The celerybeat process performs worker discovery and
  maintains a list of available workers. Additionally, it performs task
  cancellations in the event of a worker shutdown. Periodic events are kicked off
  via celerybeat, and tasks that have failed more than *X* times are
  automatically cancelled. Only one of these should be active at any time!

* ``pulp_resource_manager`` - The resource manager assigns tasks to workers. If
  it knows a worker has a task for a particular repo, it will assign other work
  for that repo to the same worker. This allows us to avoid performing multiple
  conflicting tasks on a repo at the same time. Only one of these should be
  active at any time!

Additionally, Pulp relies on other components:

* `Mongo DB <http://www.mongodb.org/>`_ - the database for Pulp
* `Apache Qpid <https://qpid.apache.org/>`_ or `RabbitMQ
  <http://www.rabbitmq.com/>`_ - the queuing system that Pulp uses to assign work
  to workers. Pulp can operate equally well with either qpid or rabbitmq.

.. WARNING:: Before we continue, it is critical to note that pulp_celerybeat
   and pulp_resource_manager should *never* have more than a single instance
   running under any circumstance!

The diagram below shows an example default deployment. Everything is running on
a single machine in this case.

.. image:: images/pulp-exp1.png

.. This section is still TODO.
.. Sizing Considerations
.. ^^^^^^^^^^^^^^^^^^^^^
.. 
.. * Storage Considerations
.. 
..   * How much disk should someone allocate to a Pulp install, and which dirs
..     should be mapped backed-up storage? Which dirs should be on local disk?
.. 
..   * When should they grow their volume?
.. 
..   * How do you recover if a volume does indeed fill up?
.. 

Choosing What to Scale
^^^^^^^^^^^^^^^^^^^^^^

Not all Pulp installations are used in the same way. One installation may have
hundreds of thousands of RPMs, another may have a smaller number of RPMs but
with lots of consumers pulling content to their systems. Others may sync
frequently from a number of upstream sources.

A good first step is to figure out how many systems will be pulling content
from your Pulp installation at any given time. This includes RPMs, Puppet
modules, Docker layers, and OSTree layers. RPMs are usually pulled down on a
regular basis as part of a system update schedule, but other types of content
might be fetched in a more ad-hoc fashion.

If the number of concurrent downloads seems large, you may want to consider
adding additional servers to service httpd requests. See "Scaling httpd"
section below for more information.

On the other hand, if you expect to maintain a large set of repositories that
get synced frequently, you may want to add additional servers for worker
processes. Worker procseses handle long-running tasks such as content downloads
from upstream sources and also perform actions like repository metadata
regeneration on publish. See the "Scaling workers" section below for more
information.

Another consideration for large sets of repositories or repositories with large
numbers of RPMs is to have a dedicated server or set of servers for Mongo DB.
Pulp does not store actual content in the database, but all metadata is stored
there. More information on Mongo DB is available on the `Mongo DB website
<http://www.mongodb.org/about/introduction/#deployment-architectures>`_

Pulp uses either RabbitMQ or Apache Qpid as its messaging backend. Pulp does
not generate many messages as compared to other applications, so it is not
expected that the messaging backend would need to be scaled for performance
unless the number of concurrent consumer connections is large. However,
additional configuration may be done to make the messaging backend more fault
tolerant. Examples of this are available for both `Apache Qpid
<https://qpid.apache.org/releases/qpid-0.28/cpp-broker/book/chapter-ha.html>`_
and `RabbitMQ <http://www.rabbitmq.com/ha.html>`_.

.. WARNING:: There is a bug in versions of Apache Qpid older than 0.30 that
   involves running out of file descriptors. This is an issue on deployments
   with large numbers of consumers. See :bz:`1122987` for more information
   about this and for suggested workarounds.


Scaling httpd Servers
^^^^^^^^^^^^^^^^^^^^^
If needed, additional httpd servers can be added to Pulp. This is done in
situations when there are more incoming HTTP or HTTPS requests than a single
server can respond to. For example, if the Apache `mod_status
<https://httpd.apache.org/docs/2.2/mod/mod_status.html>`_ scoreboard frequently
shows that all workers are busy, it may be time to add additional httpd
servers. Another reason of course would be for redundancy purposes.

.. NOTE:: Pulp iteslf does not provide httpd load balancing capabilities. A
   load balancer or proxy in front of the Pulp httpd tier will need to be
   installed and configured.

In order to add an additional httpd server, simply configure a new server in
the same fashion as your existing server. Importantly however, do *not* enable
`pulp_celerybeat`, `pulp_resource_manager`, or `pulp_workers`. Only `httpd`
should be running!

The directories `/etc/pki/pulp` and `/var/lib/pulp` need to be shared across
each httpd server, as well as each worker. This is typically done via NFS.

Scaling Pulp workers
^^^^^^^^^^^^^^^^^^^^

Additional Pulp workers can be added in the same fashion as adding additional
httpd servers above. However instead of starting `httpd`, start `pulp_workers`
instead. The same caveats apply about not inadvertently starting a second
instance of `pulp_celerybeat` or `pulp_resource_manager`.

Pulp workers work asynchronously off of a queue provided by the message broker
and do not need to be fronted by a load balancer or proxy.

The directories `/etc/pki/pulp` and `/var/lib/pulp` need to be shared across
each server that hosts workers, as well as all httpd servers. This is typically
done via NFS.

Pulp and Mongo Database
^^^^^^^^^^^^^^^^^^^^^^^
Pulp uses Mongo to manage repository information as well as content metadata.
Mongo can be run on the same machine as Pulp, but we recommend that it run on
dedicated hardware for larger production deployments. At this time, Pulp can be
used with `replication <http://docs.mongodb.org/manual/replication/>`_ but does
not support sharding.

Monitoring
----------

Monitoring for outages
^^^^^^^^^^^^^^^^^^^^^^^^

While Pulp has a number of processes, users will interact with Pulp via httpd.
At a minimum, your monitoring system should alert for the following issues:

* `httpd` is not responsive on ports 80 or 443

* storage volumes associated with Pulp are about to run out of space

* Mongo is not responsive

* Apache Qpid or RabbitMQ is not responsive

You may also want to alert if no Pulp workers are available. This is optional
since it affects long-running background tasks like syncing and publishing but
would not affect content downloads for consumer systems.

Please consult the documentation of your monitoring software for information on
how to check for these types of issues.

Monitoring for performance issues
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Performance issues fall into a number of categories. However, here are some
typical statistics that can be collected and reviewed periodically:

* work queue depth

* repository sync time

* repository publish time

* concurrent `httpd` connections to ports 80 and 443

* storage volume space usage

Many of these statistics can be collected and viewed using tools like `Celery
Flower <https://pypi.python.org/pypi/flower/>`_ or `Munin
<http://munin-monitoring.org/>`_.

