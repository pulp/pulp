Tuning and Monitoring
======================

Tuning
------

WSGI Processes
^^^^^^^^^^^^^^

By default, each Apache server on which Pulp is deployed will start 3 WSGI
processes to serve the REST API. The number of processes can be adjusted in
``/etc/httpd/conf.d/pulp.conf`` on the ``WSGIDaemonProcess`` statement, along
with other items. See the Apache documentation of ``mod_wsgi`` for details.

For tuning purposes, consider Pulp's REST API to be a low-traffic web
application that has occasional spikes in memory use when returning large data
sets. Most of pulp's heavy-lifting has been offloaded to celery workers.

Pulp and Mongo Database
^^^^^^^^^^^^^^^^^^^^^^^
Pulp uses Mongo to manage repository information as well as content metadata.
Mongo can be run on the same machine as Pulp, but we recommend that it run on
dedicated hardware for larger production deployments. At this time, Pulp can be
used with `replication <http://docs.mongodb.org/manual/replication/>`_ but does
not support sharding.

If searches for content are performing poorly, performance may be improved by adding an index for
the collection responsible for that content type. Each content type has a collection called
`unit_<type>`. More about index creation can be found here_.

.. _here: http://docs.mongodb.org/manual/core/index-creation/

Monitoring
----------

Monitoring for outages
^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
