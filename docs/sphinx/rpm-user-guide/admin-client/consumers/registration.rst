Consumer Registration
=====================

The Pulp admin client may be used to :term:`unregister <registration>` an
existing :term:`consumer`.  On successful unregistration, the consumer is
removed Pulp server's inventory and a request is sent to the consumer's agent
to clean up registration artfacts.


Unregistering an Existing Consumer
----------------------------------

The ``unregister`` command is used to unregister a consumer that has been
previously registered to a Pulp server.

The following options are required:

``--consumer-id`` 
   The unique identifier for a consumer.

  

Update a Registered Consumer
----------------------------

The ``update`` command is used to update information about a previously
registered consumer.  Only the specified fields are modified.  Unspecified fields
are unaffected by the command.

The following options are required:

``--consumer-id`` 
   The unique identifier for a consumer.

The following options are supported:

``--display-name``
  User-friendly name for the consumer.
  
``--description``
    Arbitrary, user-friendly text used to indicate the usage and content
    of the consumer.

``--note``
  Adds a single key-value pair to the consumer's metadata. Multiple pairs can
  be specified by specifying this option more than once. The value of this option
  must be specified as the key and its value separated by an equal sign. Example
  usage: ``--note k1=v1 --note k2=v2``.