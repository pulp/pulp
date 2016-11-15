Update
======

A consumer's attributes are stored on the server when it registers. Those attributes
can be updated by using the ``pulp-consumer update`` command.

::

  $ pulp-consumer update --help
  Command: update
  Description: changes metadata of this consumer

  Available Arguments:

    --display-name - user-readable display name for the consumer
    --description  - user-readable description for the consumer
    --note         - adds/updates/deletes key-value pairs to programmatically
                     identify the repository; pairs must be separated by an equal
                     sign (e.g. key=value); multiple notes can be changed by
                     specifying this option multiple times; notes are deleted by
                     specifying "" as the value

Here is an example of updating the display name:

::

  $ pulp-consumer update --display-name="Consumer 1"
  Consumer [con1] successfully updated
