Consumer
========

There are several commands for managing consumers. Other type-specific commands,
such as ``bind``, are provided by type-specific extensions.

History
-------

Pulp keeps a history of the operations that pertain to each consumer. The
``history`` command has several options for filtering and limiting its output.

::

    $ pulp-admin consumer history --help
    Command: history
    Description: displays the history of operations on a consumer

    Available Arguments:

      --consumer-id - (required) unique identifier; only alphanumeric, -, and _
                      allowed
      --event-type  - limits displayed history entries to the given type; supported
                      types: ("consumer_registered", "consumer_unregistered",
                      "repo_bound", "repo_unbound","content_unit_installed",
                      "content_unit_uninstalled", "unit_profile_changed",
                      "added_to_group","removed_from_group")
      --limit       - limits displayed history entries to the given amount (must be
                      greater than zero)
      --sort        - indicates the sort direction ("ascending" or "descending")
                      based on the entry's timestamp
      --start-date  - only return entries that occur on or after the given date in
                      iso8601 format (yyyy-mm-ddThh:mm:ssZ)
      --end-date    - only return entries that occur on or before the given date in
                      iso8601 format (yyyy-mm-ddThh:mm:ssZ)


The ``history`` command shows the most recent operations first.

::

    $ pulp-admin consumer history --consumer-id=consumer1
    +----------------------------------------------------------------------+
                            Consumer History [ consumer1 ]
    +----------------------------------------------------------------------+

    Consumer Id:  consumer1
    Type:         repo_bound
    Details:
      Distributor Id: puppet_distributor
      Repo Id:        repo1
    Originator:   admin
    Timestamp:    2013-01-22T16:07:52Z


    Consumer Id:  consumer1
    Type:         consumer_registered
    Details:      None
    Originator:   admin
    Timestamp:    2013-01-22T15:09:58Z


List
----

This command retrieves a list of consumers. "Confirmed" bindings are those for
which the agent on the remote consumer has performed a bind action. "Unconfirmed"
bindings are waiting for that remote action to take place.

::

    $ pulp-admin consumer list --help
    Command: list
    Description: lists a summary of consumers registered to the Pulp server

    Available Arguments:

      --fields   - comma-separated list of consumer fields; if specified only the
                   given fields will be displayed
      --bindings - if specified, the bindings information is displayed
      --details  - if specified, all of the consumer information is displayed

    $ pulp-admin consumer list
    +----------------------------------------------------------------------+
                                   Consumers
    +----------------------------------------------------------------------+

    Id:            consumer1
    Display Name:  Consumer 1
    Description:   The first consumer.
    Bindings:
      Confirmed:   repo1
      Unconfirmed:
    Notes:


Search
------

For a more powerful way to find and list consumers, user the :ref:`criteria`
based ``search`` command.

::

    $ pulp-admin consumer search --str-eq 'id=consumer1'
    Capabilities:
    Certificate:   -----BEGIN CERTIFICATE-----
                   MIICETCB+gIBEDANBgkqhkiG9w0BAQUFADAUMRIwEAYDVQQDEwlsb2NhbGhvc3Qw
                   HhcNMTMwMjA5MTQ1NzQ2WhcNMjMwMjA3MTQ1NzQ2WjAOMQwwCgYDVQQDEwNmb28w
                   gZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAKvJ+5XzfArVxxrm4a16UoOA7F0x
                   N++uip+GTqj/v9wG3ktHom+hlP0mlrzYOq731RS3zSBN8lkmCifRU+GKcyfG41/s
                   k1LCGLR8N2AQin8XEeKjaloG4h9Q11ZLYWWklWSAbgL1HmzFg1FNiuEH7IPUR8MW
                   PDExyOVOOHNjvhbTAgMBAAEwDQYJKoZIhvcNAQEFBQADggEBAIlpxab9wWOXczAZ
                   bL+qdIf74bQ0yPug6wn1uWR6PamSYF6BuHzZIMHyq6n1ikx+RhBE2GGt0O01yR7Q
                   Iq2zzOW80eJop5ct8pgoykVvMEG7xvF9qA2diJAi9npsA/dzvhaeyAFAcsCG60pU
                   FKSOCjG8fXhyaU6o9oqX13dRo4ahW33ofYBnC/1Ck0L19ZDm5aA7zlu12j/ssMmI
                   sDUZNzGg50lPvV58/1nalmxLWuNNScaWhOErPKowkfh8K7lcBfMVZs5H3VJQ6hW7
                   iqjFyGBtASOdgw+Nc7yCkJSvUbkV+3uhKHNF+TG0uGGGPBcyOq+qkXEBeNwLKPbL
                   taWnfe8= -----END CERTIFICATE-----
    Description:   None
    Display Name:  Consumer 1
    Id:            consumer1
    Notes:


Unregister
----------

Registration must be initiated from ``pulp-consumer``, but unregistering can be
done from either end.

::

    $ pulp-admin consumer unregister --help
    Command: unregister
    Description: unregisters a consumer

    Available Arguments:

      --consumer-id - (required) unique identifier; only alphanumeric, -, and _
                      allowed

    $ pulp-admin consumer unregister --consumer-id=consumer1
    Consumer [ consumer1 ] successfully unregistered


Update
------

Basic attributes of consumers can be modified using the ``update`` command.

::

    $ pulp-admin consumer update --help
    Command: update
    Description: changes metadata on an existing consumer

    Available Arguments:

      --display-name - user-readable display name (may contain i18n characters)
      --description  - user-readable description (may contain i18n characters)
      --note         - adds/updates/deletes notes to programmatically identify the
                       resource; key-value pairs must be separated by an equal sign
                       (e.g. key=value); multiple notes can be changed by specifying
                       this option multiple times; notes are deleted by specifying
                       "" as the value
      --consumer-id  - (required) unique identifier; only alphanumeric, -, and _
                       allowed


    $ pulp-admin consumer update --consumer-id=consumer1 --description='First consumer.'
    Consumer [ consumer1 ] successfully updated

