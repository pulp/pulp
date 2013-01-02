Authentication for the Pulp Consumer
====================================

For Pulp consumers, authentication comes in two phases: pre-registration and
post-registration. Each has their specific uses, detailed below.


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

 $ sudo pulp-consumer -u admin register --consumer-id my-consumer
 Enter password:
 Consumer [my-consumer] successfully registered

The ``-u`` and the ``-p`` flags supply the HTTP Basic Auth *username* and
*password* respectively and must correspond to a user defined on the Pulp
server. If the ``-p`` flag is not supplied, the command line client will ask for
the password interactively.


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


