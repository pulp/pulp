Glossary
========

.. Please keep glossary entries in alphabetical order

.. glossary::

  binding
    An association between a :term:`consumer` and a :term:`repository`
    :term:`distributor` for the purpose of installing :term:`content units <content unit>`
    on the specified consumer.

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

  importer
    Server-side plugin that provides support for synchronizing content from an
    external source and importing that content into the Pulp server. Importers
    are added to repositories to define the supported functionality of that
    repository.

  repository
    A collection of content units. A repository's supported types is dictated
    by the configured :term:`importer`. A repository may have multiple
    :term:`distributors <distributor>` associated which are used to publish
    its content to multiple destinations, formats, or protocols.
