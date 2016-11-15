Status
======

You can check registration status of a consumer using *pulp-consumer status* command. 
With this command you can get the information about which server the consumer is registered to 
and the consumer id used for the registration.

::

  $ pulp-consumer status
  This consumer is registered to the server [test-pulpserver.rdu] with the ID [f17-test-consumer].

When the consumer is not registered to a pulp server, it will simply display a message stating the same.

::

  $ pulp-consumer status 
  This consumer is not currently registered.
