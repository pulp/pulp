Registering
===========

In order to register a consumer against the Pulp server, the **pulp-consumer** 
command line client provides the ``register`` command. A consumer must be 
registered against a server in order to benefit from the administrative 
functionality provided by Pulp.

::

 $ sudo pulp-consumer -u admin -p admin register --consumer-id my-consumer
 Consumer [my-consumer] successfully registered


**NOTE** the **pulp-consumer** command line client must be run with *root* 
privileges and the ``register`` command uses HTTP Basic Auth credentials to 
access the Pulp server's API. The ``-u`` and ``-p`` flags must correspond to 
the *username* and *password* of a user defined on the Pulp server.

