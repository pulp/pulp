General Reference
=================

.. _coordinator-overview:

Conflicting Operations
----------------------

Pulp, by its nature, is a highly concurrent application. Everything from the
client and APIs themselves down to the need to allow long running sync processes
to execute in the background lends itself to situations where conflicting
user requests may arise.

The simplest example is a situation where a user attempts to delete a repository
in the process of being synchronized. It is the responsibility of the server
to detect these sorts of situations and preserve the integrity of its data.

The Pulp server employs a coordination layer for this purpose. The majority
of the calls made against the server are first checked to verify their ability
to run. This test will result in one of three situations:

* In many cases, the call will be queued to run at the server's earliest convenience
  (factoring in overall server load).
* If a resource is currently busy, the call may be *postponed* until the resource
  becomes available. For example, if a repository configuration update is requested
  while the repository is performing a sync, the update call will be accepted by
  the server but will not execute until the sync completes.
* In rare cases, the call may be outright *rejected* if the resource is in a state
  where the call will never execute. For example, if a call to delete a repository
  is in the queue and a call is made after that to update its configuration, the
  update call will be rejected due to the fact that the repository will be
  deleted before the update call has a chance to resolve.

The client will indicate which of the three possibilties occurred and provides
commands to work with tasks for a given resource (for instance,
the :ref:`repository tasks <repo-tasks>` series of commands).


ID Restrictions
---------------

.. _date-and-time:

Date and Time Units
-------------------

Dates and times, including intervals, are specified using the
`ISO8601 format <http://en.wikipedia.org/wiki/ISO_8601#Combined_date_and_time_representations>`_.
While it is useful to be familiar with the full specification, a summary of the
common usage patterns can be found below.

Dates are written in the format YYYY-MM-DD. For example, May 28th, 2005 is
represented as ``2005-05-28``.

Times are specified as HH:MM and should always be expressed in UTC. To mark
the time as UTC, a ``Z`` is appended to the end of the time designation. For
example, 1:45 is represented as ``01:45Z``.

These two pieces can be combined with a capital T as the delimiter. Using the
above two examples, the full date expression is ``2005-05-28T01:45Z``.

.. _date-and-time-interval:

Intervals
^^^^^^^^^

Some situations, such as scheduling a recurring operation, call for an interval
to be specified. The general syntax for an interval is to begin with a capital
P (used to designate the start of the interval, historically called a "period")
followed by the quantity of the interval and the units. For example, an interval
of three days is expressed as ``P3D``.

The following are the commonly used interval units (more are supported, these
are just a subset):

* ``D`` - Days
* ``W`` - Weeks
* ``M`` - Months
* ``Y`` - Years

Additionally, the following "time"-based intervals are supported:

* ``S`` - Seconds (likely too frequent to use in most cases)
* ``M`` - Minutes
* ``H`` - Hours

Time based intervals require a capital T prior to their definition. For example,
an interval of every 6 hours is expressed as ``PT6H``.

In many cases, Pulp allows schedules to be created with a start time in the past.
The server will apply the interval until it determines the next valid timeframe
in the future. Thus an interval defined as starting on January 1st and executing
every month, if added in mid-April, will execute for its first time on May 1st.

The interval is appended after the start time, separated by a front slash. For
example, an interval of one day starting on October 10th is represented as
``2011-10-10/P1D``.

.. _date-and-time-recurrence:

Recurrence
^^^^^^^^^^

The ISO8601 format also includes the ability to specify the number of times
an interval based operation should perform. The recurrence is defined as a
capital R and the number of times it should execute. This value is prefixed
in front of the rest of the expression and separated by a front slash. For
example, running an operation every hour for 5 runs is expressed as ``R5/PT1H``.

A recurrence expression is only valid when an interval is included as well.

Examples
^^^^^^^^

Putting it all together, below are some examples and their real world explanations:

``PT1H``
  Every hour; in most cases Pulp will default the start time if unspecified to
  the time when the server received the request.

``P2W``
  Every other week starting immediately.

``2012-01-01T00:00Z/P1M``
  The first of every month at midnight, starting at January 1st.

``R7/P1D``
  Every day for one week (techincally, for 7 days).

``R5/2007-07-05T23:16Z/P1D``
  Starting on July 5th at 11:16pm UTC, run at that time every day for the next
  5 days.