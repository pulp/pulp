Glossary
========

.. Please keep glossary entries in alphabetical order

.. glossary::
  iso8601
    ISO Date format that is able to specify an optional number of recurrences,
    an optional start time, and a time interval. There are a number of
    equivalent formats.
    Pulp supports: R<optional recurrences>/<optional start time>/P<interval>
    Examples:

    * simple daily interval: P1DT
    * 6 hour interval with 3 recurrences: R3/PT6H
    * 10 minute interval with start time: 2012-06-22T12:00:00Z/PT10M

    Further reading and more examples:
    `<http://en.wikipedia.org/wiki/ISO_8601#Time_intervals>`_
