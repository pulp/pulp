Extra Configuration
===================

SSL Configuration
-----------------

By default, all of the client components of Pulp will require validly signed SSL certificates from
the servers on remote ends of its outbound connections. On a brand new httpd installation, a
self-signed certificate will be generated for the server to use to serve Pulp. This means that a
fresh installation will experience client errors similar to this::

    (pulp)[rbarlow@coconut pulp]$ pulp-admin puppet repo list
    +----------------------------------------------------------------------+
    Puppet Repositories
    +----------------------------------------------------------------------+

    WARNING: The server's SSL certificate is untrusted!

    The server's SSL certificate was not signed by a trusted authority. This could
    be due to a man-in-the-middle attack, or it could be that the Pulp server needs
    to have its certificate signed by a trusted authority. If you are willing to
    accept the associated risks, you can set verify_ssl to False in the client
    config's [server] section to disable this check.

You have two choices to solve this issue: You may make or acquire signed SSL certificates for httpd
to use to serve Pulp, or you may configure Pulp's various clients not to perform SSL signature
validation.

.. note:

   Even Pulp's server makes client connections in some cases. For example, a Child Node will act as
   a client to its parent.


.. _signed_certificates:

Signed Certificates
^^^^^^^^^^^^^^^^^^^

If you wish to use signed certificates, you must decide whether you will purchase signed
certificates from a root certificate authority or use your own organization's certificate authority.
How to make or buy signed certificates is outside the scope of this document. We will assume that
you have these items:

#. A PEM-encoded X.509 certificate file, signed by a trusted certificate authority.
#. A PEM-encoded private key file that corresponds to your SSL certificate.
#. The CA certificate that signed your SSL certificate. This is only necessary if your Linux
   distribution does not already include the CA that signed your certificate in its system CA
   pack.

You must first configure httpd to use the SSL certificate and private key you have acquired. You
must configure the `SSLCertificateFile`_ and `SSLCertificateKeyFile`_ mod_ssl directives to point at
these files. On Red Hat based systems, these settings can be found in
``/etc/httpd/conf.d/ssl.conf``.

.. _SSLCertificateFile: https://httpd.apache.org/docs/2.2/mod/mod_ssl.html#sslcertificatefile
.. _SSLCertificateKeyFile: https://httpd.apache.org/docs/2.2/mod/mod_ssl.html#sslcertificatekeyfile

If you are using a CA certificate that is not already trusted by your operating system's system CA
pack, you may either configure Pulp to trust that CA, or you may configure your operating system to
trust that CA.

Pulp has a setting called ``ca_path`` in these files: ``/etc/pulp/admin/admin.conf``,
``/etc/pulp/consumer/consumer.conf``, and ``/etc/pulp/nodes.conf``. This setting indicates which CA
pack each of these components should use when validating Pulp server certificates. By default, Pulp
will use the operating system's CA pack. If you wish, you may adjust this setting to point to a
different CA pack. The CA pack may be a single file that contains multiple concatenated
certificates, or it may be a directory with OpenSSL style hashed symlinks pointing at CA certificate
files, with one certificate per file. Of course, if you have exactly one CA certificate, you can
configure this setting to point at it directly.

There are three settings in ``/etc/pulp/server.conf`` that you should be aware of, but probably
should not alter. ``capath`` and ``cakey`` point to a CA certificate and key that Pulp uses to sign
client authentication certificates. Note that this is not the CA that you signed your server
certificate with earlier. It is used only internally by Pulp and Apache to create client
certificates with login calls, and to validate those certificates when clients use the API. It is
best to avoid altering these settings. The third setting is confusingly named
``ssl_ca_certificate``. This setting should not be used, since it causes a chicken and egg situation
that could cause the universe to experience a machine check exception. If it is configured, the yum
consumer handlers will use this CA in their yum repository files for validating the Pulp server. The
problem is that the consumer must have already trusted Pulp in order to have registered to Pulp to
get this CA file, which helps the consumer to trust Pulp. It's best for users to configure CA trust
themselves outside of Pulp, which is why this setting should not be used.

.. warning::

   The Pulp team plans to deprecate the ``cacert``, ``cakey``, and ``ssl_ca_certificate`` settings.
   It is best to avoid altering these settings from their defaults, as described above. See
   `1123509`_ and `1165403`_.

.. _1123509: https://bugzilla.redhat.com/show_bug.cgi?id=1123509
.. _1165403: https://bugzilla.redhat.com/show_bug.cgi?id=1165403

If you want to use SSL with Qpid, see the
:ref:`Qpid SSL Configuration Guide <qpid-ssl-configuration>`.


Turning off Validation
^^^^^^^^^^^^^^^^^^^^^^

.. warning::

   It is strongly recommended that you make or acquire
   :ref:`signed certificates <signed_certificates>` to prevent man-in-the-middle attacks or other
   nefarious activities. It is very risky to assume that the other end of the connection is who
   they claim to be. SSL uses a combination of encryption and authentication to ensure private
   communication. Disabling these settings removes the authentication component from the SSL
   session, which removes the guarantee of private communication since you can't be sure who you
   are communicating with.

Pulp has a setting called ``verify_ssl`` in these files: ``/etc/pulp/admin/admin.conf``,
``/etc/pulp/consumer/consumer.conf``, ``/etc/pulp/nodes.conf``, and ``/etc/pulp/repo_auth.conf``. If
you configure these settings to false, the respective Pulp components will no longer validate the
Pulp server's certificate signature.


Pulp Broker Settings
--------------------

To configure Pulp to work with a non-default broker configuration read the
:ref:`Pulp Broker Settings Guide <pulp-broker-settings>`.


MongoDB Authentication
----------------------

To configure Pulp for connecting to the MongoDB with username/password authentication, use the
following steps:

#. Configure MongoDB for username password authentication. See
   `MongoDB - Enable Authentication <http://docs.mongodb.org/manual/tutorial/enable-authentication/>`_
   for details.

#. In ``/etc/pulp/server.conf``, find the ``[database]`` section and edit the ``username`` and
   ``password`` values to match the user configured in step 1.

#. Restart all of Pulp's services. For systemd::

      $ sudo systemctl restart httpd pulp_workers pulp_resource_manager pulp_celerybeat

   For Upstart::

      $ for s in httpd pulp_workers pulp_resource_manager pulp_celerybeat; do sudo service $s restart; done;

Logging Configuration
---------------------

.. _logging:

Logging
-------

.. note::

   Pulp reads the log configuration during startup. If the log level is changed while Pulp is
   running, then you will need to restart it.


Log Type
^^^^^^^^

Pulp's log type can be adjusted with the ``log_type`` setting in the ``[server]`` section of
``/etc/pulp/server.conf``. This setting is optional and defaults to syslog. Valid choices are
syslog and console.

Log Level
^^^^^^^^^

Pulp's log level can be adjusted with the ``log_level`` setting in the ``[server]`` section of
``/etc/pulp/server.conf``. This setting is optional and defaults to INFO. Valid choices are
CRITICAL, ERROR, WARNING, INFO, DEBUG, and NOTSET.

.. note::

   This setting will only adjust the verbosity of the messages that Pulp emits. If you wish to see
   all of these messages, you may also need to set the log level on your syslog handler. For example,
   rsyslog typically only displays INFO and higher, so if you set Pulp to DEBUG it will still be
   filtered by rsyslog. See the :ref:`rsyslogd` section for more information.

Why Syslog?
^^^^^^^^^^^

Pulp's use of syslog is a departure from previous Pulp releases which used to write their own log
files to /var/log/pulp/. This was problematic for Pulp's 2.4.0 release as Pulp evolved to use a
multi-process distributed architecture. Python's file-based log handler cannot be used by multiple
processes to write to the same file path, and so Pulp had to do something different. Syslog is a
widely used logging protocol, and given the distributed nature of Pulp it was the most appropriate
logging solution available.

Task ID
^^^^^^^

Since Pulp is a multi-process application, Pulp will attempt to log a shortened 8 character version
of the task id if the log entry is emitted from a task process. This can be used to look up the task
in ``pulp-admin tasks`` commands.  An example of a log statement with a task id would be::

    Jan 20 23:12:02 myhost pulp[30687]: pulp_rpm.plugins.importers.yum.sync:INFO: [338bdde4] Downloading 32 RPMs

Here the shortened task id is ``338bdde4``. The full task id would be
``338bdde4-608a-44ab-a79c-49c28b0fe037``. A statement without a task id would look like::

    Jan 21 23:12:02 myhost pulp[30482]: pulp.server.async.worker_watcher:INFO: New worker 'resource_manager@myhost' discovered

.. _maintenance_job:

Maintenance Job
---------------

Pulp has a maintenance job that deletes orphaned applicability profile data generated when using
Pulp with consumers. This job runs monthly, but due to how Celery uses the periodic task feature, it
only runs if the process stays running longer than 30 days. In environments where process restarts
occur more frequently, it is recommended to configure a cron job to run the following script weekly
or monthly::

    celery -A pulp.server.async.app call pulp.server.maintenance.monthly.queue_monthly_maintenance

There is an rpm available that will install this command as a weekly cronjob named
`pulp-maintenance`. Install it on one of your Pulp servers using::

    sudo dnf install pulp-maintenance
