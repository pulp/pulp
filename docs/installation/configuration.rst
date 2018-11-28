Configuration
=============

.. _configuration:

-----------

Pulp uses `dynaconf <https://dynaconf.readthedocs.io/en/latest/>`_ for its settings. dynaconf
allows storing `settings in multiple file formats <https://dynaconf.readthedocs
.io/en/latest/guides/examples.html>`_. By default Pulp looks for settings in ``/etc/pulp/settings
.py``. An alternate location for the settings file is specified by setting the ``PULP_SETTINGS``
environment variable. Each of the settings can also be set by prepending ``PULP_`` to the name
and setting it as an environment variable. The comprehensive list of settings can be found in
`Django docs <https://docs.djangoproject.com/en/2.1/ref/settings/>`_. `Environment variables
<https://dynaconf.readthedocs.io/en/latest/guides/environment_variables
.html#environment-variables>`_ take precedence over all other configuration sources. `TOML inline
table notation <https://github.com/toml-lang/toml#inline-table>`_ should be used to express any
nested environment variables such as ``PULP_LOGGING`` or ``PULP_DATABASES``. Python is the
recommended language for expressing configuration in a settings file.

SECRET_KEY
^^^^^^^^^^

    In order to get a pulp server up and running a `Django SECRET_KEY
    <https://docs.djangoproject.com/en/2.1/ref/settings/#secret-key>`_ *must* be
    provided.

    The following code snippet can be used to generate a random SECRET_KEY.

.. code-block:: python
   :linenos:

   import random

   chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
   print(''.join(random.choice(chars) for i in range(50)))

DATABASES
^^^^^^^^^

   By default Pulp uses PostgreSQL on localhost. For all possible configurations please refer to
   `Django documentation on databases <https://docs.djangoproject.com/en/2
   .1/ref/settings/#databases>`_

LOGGING
^^^^^^^

   By default Pulp logs at an INFO level to syslog. For all possible configurations please
   refer to `Django documenation on logging <https://docs.djangoproject.com/en/2
   .1/topics/logging/#configuring-logging>`_.

WORKING_DIRECTORY
^^^^^^^^^^^^^^^^^

   The directory used by workers to store files temporarily. This defaults to
   ``/var/lib/pulp/tmp/``.


REDIS_HOST
^^^^^^^^^^

   The hostname for Redis. By default Pulp will try to connect to Redis on localhost. `RQ
   documentation <https://python-rq.org/docs/workers/>`_ contains other Redis settings
   supported by RQ.

REDIS_PORT
^^^^^^^^^^

   The port for Redis. By default Pulp will try to connect to Redis on port 6380.

REDIS_PASSWORD
^^^^^^^^^^^^^^

   The password for Redis.


CONTENT
^^^^^^^

   Configuration for the content app. Pulp defaults to using the Django web server to serve
   content.

   WEB_SERVER
     Defines the type of web server that is running the content application.
     When set to `django`, the content is streamed.
     When set to `apache`, the `X-SENDFILE` header is injected which delegates
     streaming the content to Apache.  This requires
     `mod_xsendfile <https://tn123.org/mod_xsendfile/>`_ to be installed.

     When set to `nginx`, the `X-Accel-Redirect` header is injected which delegates
     streaming the content to NGINX.

     Below is the default configuration written in Python.

.. code-block:: python
   :linenos:

   CONTENT = {
      'HOST': None,
      'WEB_SERVER': 'django',
      'REDIRECT': {
         'HOST': None,
         'PORT': 443,
          'PATH_PREFIX': '/streamer/',
        'ENABLED': False,
      }
   }

PROFILE_STAGES_API
^^^^^^^^^^^^^^^^^^

   A debugging feature that collects profile data about the Stages API as it runs. See
   :ref:`stages-api-profiling-docs` for more information.
