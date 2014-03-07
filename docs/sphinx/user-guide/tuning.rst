Tuning
======

WSGI Processes
--------------

By default, each system on which pulp is deployed will start 3 WSGI processes to
serve the REST API. The number of processes can be adjusted in
``/etc/httpd/conf.d/pulp.conf`` on the ``WSGIDaemonProcess`` statement, along
with other items. See the Apache documentation of ``mod_wsgi`` for details.

For tuning purposes, consider pulp's REST API to be a low-traffic web
application that has occasional spikes in memory use when returning large data
sets. Most of pulp's heavy-lifting has been offloaded to celery workers.