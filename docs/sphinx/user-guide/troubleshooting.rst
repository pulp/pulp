Troubleshooting
===============


Log File Locations
------------------

/var/log/pulp/celerybeat.log
  Celery beat log

/var/log/pulp/db.log
  Database log

/var/log/pulp/pulp.log
  Pulp server logs its activity here

/var/log/pulp/reserved_resource_worker-\*.log
  There will be one of these per task worker

/var/log/pulp/resource_manager.log
  The special resource manager worker's log

/var/log/httpd/error_log
  This is where Apache will log errors that the Pulp server itself did not
  handle. Bootstrap errors often get logged here.

/var/log/httpd/ssl_error_log
  This is where Apache will log errors that the Pulp server itself did not
  handle. 5xx level HTTP response codes generally get logged here, often with
  a stack trace or other information that can help a developer determine what
  went wrong.

~/.pulp/admin.log
  pulp-admin logs its activity here.

~/.pulp/consumer.log
  pulp-consumer logs its activity here.

~/.pulp/server_calls.log
  HTTP requests and responses get logged by the admin client in
  this file. To enable/disable this, consult the ``[logging]`` section of
  ``/etc/pulp/admin/admin.conf``.

~/.pulp/consumer_server_calls.log
  HTTP requests and responses get logged by the consumer client in
  this file. To enable/disable this, consult the ``[logging]`` section of
  ``/etc/pulp/consumer/consumer.conf``.

Common Issues
-------------

The server hostname configured on the client did not match the name found in the server's SSL certificate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In some distributions, such as RHEL 6.3 and Fedora 17, the default SSL certificate
used by Apache is created with its Common Name set to the hostname of the machine.
This can cause Pulp to return an error similar to ``The server hostname configured
on the client did not match the name found in the server's SSL certificate.``

If you want to connect to localhost, you need to regenerate this certificate,
which is stored in /etc/pki/tls/certs/localhost.crt. For testing purposes, delete
it, then run ``make testcert``. Be sure to answer "localhost" for the
"Common Name". Other responses do not matter.

For production installations of Pulp, it is up to the installer to provide
appropriate SSL certificates and configure Apache to use them.


Sync from within /tmp fails to find files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you experience a problem where Pulp cannot find content that is in /tmp, please
move that content outside of /tmp and try again.

A sync operation can use a local filesystem path on the server by specifying the feed
URL starting with ``file:///``. If the content is within /tmp, Apache may fail to
read that content on distributions such as Fedora that use
`private /tmp <http://fedoraproject.org/wiki/Features/ServicesPrivateTmp>`_ directories.
Since /tmp is temporary and may not persist through a system reboot, it is not
generally the best place to put important content anyway.


apr_sockaddr_info_get() failed error when starting apache on F18
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You may run into apr_sockaddr_info_get() failed error when starting apache on F18.
This is because of incorrect hostname configuration. Make sure your /etc/hosts file
contains the hostname of your machine as returned by the 'hostname' command. If not, update
/etc/hosts and run 'apachectl restart'. 

