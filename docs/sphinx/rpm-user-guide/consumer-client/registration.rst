Consumer Registration
=====================

The Pulp consumer client may be used to register a new :term:`consumer` or
to unregister an existing consumer.  Once the :term:`registration` has succeeded,
a consumer is placed into the Pulp server's inventory and associated with
credentials for accessing content.  These credentials are stored on the
consumer's filesystem.  Upon successful registration, the :term:`agent` to become
active if installed and running.  When activated, the agent will establish
communication with the Pulp server and begin processing command & control 
requests.  The agent will also begin scheduled reporting.

Registering a New Consumer
--------------------------

The ``register`` command is used to register the consumer to a pulp server.  A
pulp `username` and `password` must be specifed for authentication and
authorization.

The following options are specified before the ``register`` keyword:

``-u <username>``
  The username.
  
``-p <password>``
  The password for the specified user.
  
The following options are specified after the ``register`` keyword:

``--consumer-id``
  Unique identifier for the consumer. Valid characters include letters,
  numbers, hyphen (``-``) and underscore (``_``). The ID is case sensitive;
  "joe" and "Joe" are two separate consumers. An ID is required at consumer
  creation time.
  
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


Unregistering an Existing Consumer
----------------------------------

The ``unregister`` command is used to unregister the consumer that has been
previously registered to a pulp server.

The following options are supported:

``--force``
  When specified, the local registration artifacts stored on the consumer
  are removed regardless of whether the Pulp server can be notified of the
  unregistration.  These artifacts include credentials such as X.509 certificates
  and repository access files.

  
Check Registration Status
-------------------------

The ``status`` command is used to check the :term:`registration` status of the
consumer.


Update a Registered Consumer
----------------------------

The ``update`` command is used to update information about a previously
:term:`registered <registration>` consumer.

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