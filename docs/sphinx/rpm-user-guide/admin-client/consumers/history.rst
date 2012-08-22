History
=======

The consumer ``history`` command is used to view a :term:`consumer's <consumer>`
history.  A consumer's history is expressed as a chronologically ordered set of
pre-defined events.  Each event represents an action taken on the consumer or an
activity in which the consumer participates.

The list of tracked events on a consumer is as follows:

``consumer_registered``
  The consumer has been registered to the Pulp server.

``consumer_unregistered``
  The consumer has been unregistered.

``repo_bound``
  The consumer has been :term:`bound <binding>` to a :term:`repository`.

``repo_unbound``
  The consumer has been :term:`unbound <binding>` from a :term:`repository`.

``content_unit_installed``
  One or more :term:`content units <content unit>` has been installed on the consumer.

``content_unit_uninstalled``
  One or more :term:`content units <content unit>` has been uninstalled from the consumer.

``unit_profile_changed``
  The consumer's installed :term:`content unit` profile has been updated.

``added_to_group``
  The consumer has been added as a member of a consumer group.

``removed_from_group``
  The consumer has been removed from a consumer group.

Information displayed can be filtered using any combination of the optional
parameters listed below.

The following parameters are required:

``--consumer-id`` 
   The unique identifier for a consumer.

Filtering
^^^^^^^^^

``--event-type``
  Limits displayed history entries to the specified type.

``--start-date``
  Display entries that occur on or *after* the specified :term:`iso8601` date.

``--end-date``
  Display entries that occur on or *before* the specified :term:`iso8601` date.

``--limit``
  Limits displayed history entries to the given amount (must be
  greater than zero).

Sorting
^^^^^^^

``--sort``
  indicates the sort direction (``ascending`` or ``descending``)
  based on the entry's timestamp.
