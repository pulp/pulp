Configuration Files
===================

.. _server-conf:

server.yaml
-----------

Pulp's server configuration file is located by default at `/etc/pulp/server.yaml`, but you can
also set the `PULP_SETTINGS` environment variable to specify a custom location.

SECRET_KEY
^^^^^^^^^^

    In order to get a pulp server up and running a `Django SECRET_KEY
    <https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-secret_key>`_ *must* be
    provided in server.yaml. It is highly recommend that this SECRET_KEY be enclosed in single quotes,
    so yaml string escaping does not to be dealt with.

    The following code snippet can be used to generate a random SECRET_KEY.

.. code-block:: python
   :linenos:

   import random;

   chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
   print(''.join(random.choice(chars) for i in range(50)))

logging
^^^^^^^

    By default Pulp logs at an INFO level to syslog. Pulp also comes with a `console` handler.
    Additional handlers can be defined and used like so:

.. code-block:: yaml
   :linenos:

   logging:
     handlers:
       myCustomHandler:
         class: logging.FileHandler
         filename: /path/to/debug.log
     loggers:
       '':
         handlers: ["myCustomHandler"]
         level: DEBUG

CONTENT
^^^^^^^

WEB_SERVER
  Defines the type of web server that is running the content application.
  When set to `django`, the content is streamed.
  When set to `apache`, the `X-SENDFILE` header is injected which delegates
  streaming the content to Apache.  This requires
  `mod_xsendfile <https://tn123.org/mod_xsendfile/>`_ to be installed.

  When set to `nginx`, the `X-Accel-Redirect` header is injected which delegates
  streaming the content to NGINX.
