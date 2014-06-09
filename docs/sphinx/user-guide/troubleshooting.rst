Troubleshooting
===============

.. _logging:

Logging
-------

Starting with 2.4.0, Pulp uses syslog for its log messages. How to read Pulp's log messages
therefore depends on which log handler your operating system uses. Two different log handlers that
are commonly used will be documented here, journald and rsyslogd. If you happen to use a different
syslog handler on your operating system, please refer to its documentation to learn how to access
Pulp's log messages.

Log Level
^^^^^^^^^

Pulp's log level can be adjusted with the ``log_level`` setting in the ``[server]`` section of
``/etc/pulp/server.conf``. This setting is optional and defaults to INFO. Valid choices are
CRITICAL, ERROR, WARNING, INFO, DEBUG, and NOTSET.

journald
^^^^^^^^

journald is the logging daemon that is distributed as part of systemd. If you are using Fedora
this is your primary logging daemon, though it's possible that you also have rsyslogd installed.
journald is a very nice logging daemon that provides a very useful interface to the logs,
`journalctl <http://www.freedesktop.org/software/systemd/man/journalctl.html>`_. If your system
uses journald, you might not have any logs written to /var/log depending on how your system is
configured. For Pulp's purposes, you should use ``journalctl`` to access Pulp's various logs. Most
of the log messages that you will wish to see will have the "pulp" tag on them, so this command
will display most of Pulp's log messages::

    $ sudo journalctl SYSLOG_IDENTIFIER=pulp

We'll leave it to the systemd team to thoroughly document ``journalctl``, but it's worth mentioning
that it can be used to aggregate the logs from Pulp's various processes together into one handy
view using it's ``+`` operator. Pulp server runs in a variety of units, and if there are problems
starting Pulp, you may wish to see log messages from httpd or celery. If you wanted to see the
log messages from all server processes together you could use this command::

    $ sudo journalctl SYSLOG_IDENTIFIER=pulp + SYSLOG_IDENTIFIER=celery + SYSLOG_IDENTIFIER=httpd

A ``journalctl`` flag to know about is ``-f``, which performs a similar function
as ``tail``'s ``-f`` flag.

rsyslogd
^^^^^^^^

rsyslogd is another popular logging daemon. If you are using RHEL 6, this is your logging daemon.
On many distributions, it is configured to log most messages to ``/var/log/messages``. If this is
your logging daemon, it is likely that all of Pulp's logs will go to this file by default. If you
wish to filter Pulp's log messages out and place them into a separate file, you will need to
configure rsyslogd to match Pulp's messages. Pulp prefixes all of its log messages with "pulp", to
aid in matching its messages in the logging daemon.

If you wish to match Pulp messages and have them logged to a different file than
``/var/log/messages``, you may adjust your ``/etc/rsyslog.conf`` file. You should find the line for
logging to ``/var/log/messages`` and add ``pulp.none`` to the list of its matches. This will
prevent Pulp logs from going to that file. After that, you can add a line to capture the Pulp
messages and send them to a file::

    pulp.*  /var/log/pulp.log

Why Syslog?
^^^^^^^^^^^

Pulp's use of syslog is a departure from previous Pulp releases which used to write their own log
files to /var/log/pulp/. This was problematic for Pulp's 2.4.0 release as Pulp evolved to use a
multi-process distributed architecture. Python's file-based log handler cannot be used by multiple
processes to write to the same file path, and so Pulp had to do something different. Syslog is a
widely used logging protocol, and given the distributed nature of Pulp it was the most appropriate
logging solution available.

Other logs
^^^^^^^^^^

Some of Pulp's other processes still log to files. Those file locations are documented here.

/var/log/pulp/celerybeat.log, /var/log/pulp/reserved_resource_worker-\*.log, /var/log/pulp/resource_manager.log
  All of these files will only be present if your operating system uses Upstart for init. If you
  use systemd, these log messages will all be sent to the syslog by the Celery units.

  These files will contain messages from Celery's early startup, before it initializes the Pulp
  application. If there are problems loading Pulp, Celery will log those problems here. Once Pulp
  initializes, it begins capturing all of the Celery logs and writing them to syslog.

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


Qpid connection issues when starting services or executing tasks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When setting up Pulp, or adjusting its configuration, you may encounter connection issues between
Pulp and Qpid.  If Pulp services cannot connect to the Qpid broker then Pulp cannot continue. The
most common root cause of this issue is the Qpid broker not being configured as expected due to
changes being put into a ``qpidd.conf`` that the Qpid broker is not reading from.  For Qpid 0.24+
the qpidd.conf file should be located at ``/etc/qpid/qpidd.conf`` and for earlier Qpid versions, it
should be located at ``/etc/qpidd.conf``.  The user who you run qpidd as must be able to read the
``qpidd.conf`` file.


I see 'NotFound: no such queue: pulp.task' in the logs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is experienced on a Pulp installation that uses Qpid 0.18 or earlier, and does not have the
qpid-cpp-server-store package installed with their broker. Later version of Qpid do not require this
package to be installed. This exception may not occur until the Qpid broker is restarted
unexpectedly with other Pulp services running. The exception is shown as Pulp recovers from a Qpid
availability issue.

No available workers
^^^^^^^^^^^^^^^^^^^^

Pulp requires three Celery services to be running: ``pulp_celerybeat``, ``pulp_resource_manager``,
and ``pulp_workers``. If you are experiencing this error, you may see a message similar to "There
are no Celery workers found in the system for reserved task work. Please ensure that there is at
least one Celery worker running, and that the celerybeat service is also running." in the logs or
from the CLI. Pulp will not work correctly if any of the required services are not running, so
please ensure that they are all started and configured to start after a reboot.

.. note::

   If you are using systemd, the pulp_workers service is really a proxy that starts pulp_worker-0,
   pulp_worker-1, pulp_worker-2... and so forth, depending on the number of workers you have
   configured. ``systemctl status pulp_workers`` will not report status on the real workers, but
   rather will report status on itself. Therefore if you see a successful status from pulp_workers
   it only means that it was able to start pulp_worker-0, pulp_worker-1, etc. It does not mean that
   those services are still running. It is possible to ask for pulp_worker statuses using wildcards,
   such as ``systemctl status pulp_worker-\* -a``, for example.

.. warning::

   Remember that ``pulp_celerybeat`` and ``pulp_resource_manager`` must be singletons across the
   entire Pulp distributed installation. Please be sure to only start one instance of each of these.
   ``pulp_workers`` is safe to start on as many machines as you like.

qpid.messaging is not installed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are using Qpid as your message broker, you will need the Python package ``qpid.messaging``.
On Red Hat operating systems, this is provided by the ``python-qpid`` package.

qpidtoollibs is not installed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are using Qpid as your message broker, you will also need the Python package
``qpidtoollibs``. On Red Hat operating systems, this is provided by the python-qpid-qmf package.
