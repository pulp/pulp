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

JWT_AUTH
^^^^^^^^

The configuration section for `JSON Web Tokens <https://jwt.io/>`_ authentication.

JWT_VERIFY_EXPIRATION
  You can turn off JWT token expiration time verification by setting
  `JWT_VERIFY_EXPIRATION` to `False`. Without expiration verification, tokens will last forever
  meaning a leaked token could be used by an attacker indefinitely (token can be
  invalidated by changing user's secret, which will lead to invalidation of all user's tokens).

  Default is `True`.

JWT_EXPIRATION_DELTA
  This is number of seconds for which is token valid if `JWT_VERIFY_EXPIRATION` enabled.

  Default is `1209600`. (14 days)

  .. warning::
    Change of this value will affect only newly generated tokens.

JWT_ALLOW_SETTING_USER_SECRET
  Allow setting user's secret via REST API. This is needed for offline token generation.

  Default is `False`.

JWT_AUTH_HEADER_PREFIX
  Change the prefix in the Authorization header of requests that use JWT authentication.

  Default is `Bearer`.
