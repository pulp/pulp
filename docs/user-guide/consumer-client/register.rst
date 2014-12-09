Registering
===========

In order to register a consumer against the Pulp server, the **pulp-consumer**
command line client provides the ``register`` command. A consumer must be
registered against a server in order to benefit from the administrative
functionality provided by Pulp.

::

 $ sudo pulp-consumer register --consumer-id my-consumer
 Enter password:
 Consumer [my-consumer] successfully registered


Pre-Registration Authentication
-------------------------------

The Pulp server's API is protected by basic authentication requirements. This
means that the API is only accessible by defined users with the appropriate
credentials.

Before a consumer is registered against a server, the server has no idea who
(or what) the consumer is. In order to authenticate against the server's API to
register the consumer, basic HTTP Auth credentials must be supplied along with
the registration request.

.. note::
 The **pulp-consumer** command must be executed with *root* permissions.

::

 $ sudo pulp-consumer register --consumer-id my-consumer
 Enter password:
 Consumer [my-consumer] successfully registered

The ``-u`` and the ``-p`` flags supply the HTTP Basic Auth *username* and
*password* respectively and must correspond to a user defined on the Pulp
server. If the ``-p`` flag is not supplied, the command line client will ask for
the password interactively.

.. warning::
 Entering a password on the command line with the ``-p`` option is less secure
 than giving it interactively. The password will be visible to all users on the
 system for as long as the process is running by looking at the process list.
 It will also be stored in your bash history.


Post-Registration Authentication
--------------------------------

Once a consumer is registered, a certificate is written into its PKI:
``/etc/pki/pulp/consumer/consumer-cert.pem``

This certificate will automatically suffice for authentication against the
server's API for all future operations until the consumer is unregistered.

It is worth noting that the **pulp-consumer** command line client should still
be executed with *root* level permissions.

::

 $ sudo pulp-consumer unregister
 Consumer [my-consumer] successfully unregistered
