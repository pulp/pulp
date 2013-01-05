Introducing the Pulp Consumer Client
====================================

The Pulp consumer client, **pulp-consumer**, is a command line tool that allows 
administrators to register a consumer, bind that consumer to Pulp managed 
repositories, and install content onto the consumer from those bound 
repositories.

The client requires the Pulp Agent to be installed in order to communicate with 
the Pulp server. This is a daemon process that listens on an AMQP bus for 
messages from the server and uses the bus to send messages to the server.

This page gives a brief introduction to the consumer client and the agent.


Local v. Remote Commands
------------------------

The **pulp-consumer** command line client is used to execute Pulp commands 
locally on the consumer machine. Pulp commands may be executed remotely, from 
the server, using the **pulp-admin** command line client. Details on the latter 
are covered in the **pulp-admin** documentation.

All commands are available locally. And some commands, namely ``register`` are 
only available locally.


Local Permissions
-----------------

It is imperative that the **pulp-consumer** command line client be execute with 
enough permissions to write system-level configuration and credential files. In 
general, this will mean with ``root`` privileges. This is easiest with the 
``sudo`` command.

::

 $ sudo pulp-consumer ...


