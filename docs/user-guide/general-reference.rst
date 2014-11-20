General Reference
=================

.. _resource-ids:

Resource IDs
------------

All resource ID values must contain only letters, numbers, underscores,
and hyphens.

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

.. _criteria:

Criteria
--------

Pulp offers a standard search interface across all resource types. This
interface is used in two different ways:

* As a query syntax to scope the resources returned, data retrieved for each
  resource, and pagination constructs such as limits and skips.
* As a matching syntax, used when indicating resources that should be included
  in an operation.

In other words, the same parameters used to search for specific resources can then
be fed into an operation that affects matching resources. For example, a query
can be passed to the repository search to determine which repositories match.
The same query can then be passed into the repository group membership command
to add all matching repositories to a particular group.

Where applicable, the client supports a number of arguments for describing
the desired query. More information on each argument can be found using the
``--help`` argument on the command in question.

An example of this functionality is the ``pulp-admin rpm repo search`` command.
The output of the usage text for that command is as follows::

 Command: search
 Description: searches for RPM repositories on the server

 Available Arguments:

  --filters - filters provided as JSON in mongo syntax. This will override any
              options specified from the 'Filters' section below.
  --limit   - max number of items to return
  --skip    - number of items to skip
  --sort    - field name, a comma, and either the word "ascending" or
              "descending". The comma and direction are optional, and the
              direction defaults to ascending. Do not put a space before or
              after the comma. For multiple fields, use this option multiple
              times. Each one will be applied in the order supplied.
  --fields  - comma-separated list of resource fields. Do not include spaces.
              Default is all fields.

 Filters
  These are basic filtering options that will be AND'd together. These will be
  ignored if --filters= is specified. Any option may be specified multiple
  times. The value for each option should be a field name and value to match
  against, specified as "name=value". Example: $ pulp-admin repo search
  --str-eq="id=<repo_id>"

  --str-eq - match where a named attribute equals a string value exactly.
  --int-eq - match where a named attribute equals an int value exactly.
  --match  - for a named attribute, match a regular expression using the mongo
             regex engine.
  --in     - for a named attribute, match where value is in the provided list of
             values, expressed as one row of CSV
  --not    - field and expression to omit when determining units for inclusion
  --gt     - matches resources whose value for the specified field is greater
             than the given value
  --gte    - matches resources whose value for the specified field is greater
             than or equal to the given value
  --lt     - matches resources whose value for the specified field is less than
             the given value
  --lte    - matches resources whose value for the specified field is less than
             or equal to the given value

.. _unit_association_criteria:

Unit Association Criteria
^^^^^^^^^^^^^^^^^^^^^^^^^

The criteria when dealing with units in a repository is slightly different
from the standard model. The metadata about the unit itself is split apart from
the metadata about when and how it was associated to the repository. This split
occurs in the filters, sort, and fields sections.

The primary differences are as follows:

* There are two added search criteria, ``--after`` and ``--before``. These
  fields apply to the point at which the unit was first added to the repository.
  The values for these fields are expressed as an :term:`iso8601` timestamp.
* A ``--details`` flag is provided when searching for units within a repository.
  If specified, information about the association between the unit and the
  repository will be displayed in addition to the metadata about the unit itself.

.. _client-booleans:

Client Argument Boolean Values
------------------------------

Depending on the situation, booleans are expressed in one of two ways in the
client:

Flags are used to indicate the behavior of the immediate command::

  $ pulp-admin repo list --details

Boolean values are specified for cases where the value is saved::

  $ pulp-admin rpm repo create --repo-id foo --verify-feed-ssl true
  $ pulp-admin rpm repo create --repo-id foo --verify-feed-ssl false

.. _services:

Services
--------
The platform includes several services which can be managed using standard system
tools such as *upstart* and *systemd*.

For further information:

* For upstart: ``$ man service``. Pulp init.d scripts support the following actions:

 - start
 - restart
 - status
 - stop

* For systemd: ``$ man systemctl``
