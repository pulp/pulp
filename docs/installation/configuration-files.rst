Configuration Files
===================

.. _server-conf:

server.yaml
-----------

Pulp's server configuration file should be located at `/etc/pulp/server.yaml`

SECRET_KEY
    In order to get a pulp server up and running a `Django SECRET_KEY
    <https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-SECRET_KEY>`_ *must* be
    provided in server.yaml. It is highly recommend that this SECRET_KEY be enclosed in single quotes,
    so yaml string escaping does not to be dealt with.

    The following code snippet can be used to generate a random SECRET_KEY.

.. code-block:: python
   :linenos:

   import random;

   chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
   print(''.join(random.choice(chars) for i in range(50)))

logging
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
