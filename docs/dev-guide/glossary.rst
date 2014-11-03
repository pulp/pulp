Glossary
========

.. Please keep glossary entries in alphabetical order

.. glossary::

  applicability data
    Applicability data for a consumer consists of arrays of applicable :term:`content unit` ids,
    keyed by a content unit type. The definition of applicability itself defers for each content type. 
    For example, in case of an rpm, a content unit is considered applicable to a consumer 
    when an older version of the content unit installed on that consumer can be updated 
    to the given content unit.

  binding
    An association between a :term:`consumer` and a :term:`repository`
    :term:`distributor` for the purpose of installing :term:`content units <content unit>`
    on the specified consumer.

  call report
    A JSON object describing metadata, progress information, and the final result
    of any asynchronous task being executed by Pulp.

  conduit
    Object passed to a plugin when it is invoked. The conduit contains methods the plugin
    should use to access the Pulp Server or Pulp Agent.

  consumer
    A managed system that is the consumer of content.  Consumption refers
    to the installation of software contained within a :term:`repository` and
    published by an associated :term:`distributor`.

  content unit
    An individual piece of content managed by the Pulp server. A unit does not
    necessarily correspond to a file. It is possible that a content unit is
    defined as the aggregation of other content units as a grouping mechanism.

  distributor
    Server-side plugin that takes content from a repository and publishes it
    for consumption. The process by which a distributor publishes content varies
    based on the desired approach of the distributor. A repository may have
    more than one distributor associated with it at a given time.

  extension
    Client-side command line interface plugin that provides additional commands
    within the command-line clients.

  handler
    Agent plugin that implements content type specific or operating system specific
    operations on the consumer.

  importer
    Server-side plugin that provides support for synchronizing content from an
    external source and importing that content into the Pulp server. Importers
    are added to repositories to define the supported functionality of that
    repository.

  iso8601 interval
    ISO Date format that is able to specify an optional number of recurrences,
    an optional start time, and a time interval. There are a number of
    equivalent formats.
    Pulp supports: R<optional recurrences>/<optional start time>/P<interval>
    Examples:

    * simple daily interval: P1DT
    * 6 hour interval with 3 recurrences: R3/PT6H
    * 10 minute interval with start time: 2012-06-22T12:00:00Z/PT10M

    Further reading and more examples:
    http://en.wikipedia.org/wiki/ISO_8601#Time_intervals

  platform
    Short for the "Pulp Platform", which refers to the generic framework
    functionality provided by Pulp. The platform has no type-specific knowledge;
    all type-specific functionality is provided through plugins to the platform.

  repository
    A collection of content units. A repository's supported types is dictated
    by the configured :term:`importer`. A repository may have multiple
    :term:`distributors <distributor>` associated which are used to publish
    its content to multiple destinations, formats, or protocols.

  scratchpad
    Persisted area in which a plugin may store information to be retained across
    multiple invocations. Each scratchpad is scoped to an individual plugin on a repository.

  unit profile
    An array of :term:`content unit` installed on a :term:`consumer`.  The
    structure and content of each item in the profile varies based on the
    unit type.
