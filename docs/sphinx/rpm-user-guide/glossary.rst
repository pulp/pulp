Glossary
========

.. Please keep glossary entries in alphabetical order

.. glossary::

  agent
    A daemon (service) running on a consumer.  The agent provides a command
    & control API which is used by the Pulp server to affect content changes
    on the consumer.  It also sends scheduled reports concerning consumer
    status and installed content profiles to the Pulp server.

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
    
  registration
    The association of a :term:`consumer` to a Pulp server.  Once registered,
    a consumer has access to content.
    
  importer
    Server-side plugin that provides support for synchronizing content from an
    external source and importing that content into the Pulp server. Importers
    are added to repositories to define the supported functionality of that
    repository.

  iso8601
    ISO Date format that is able to specify an optional number of recurrences,
    an optional start time, and a time interval. More information can be
    found :ref:`in the conventions section of this guide <date-and-time>`.

  repository
    A collection of content units. A repository's supported types is dictated
    by the configured :term:`importer`. A repository may have multiple
    :term:`distributors <distributor>` associated which are used to publish
    its content to multiple destinations, formats, or protocols.

  unit profile
    A list of :term:`content unit` installed on a :term:`consumer`.  The
    structure and content of each item in the profile varies based on the
    unit type.