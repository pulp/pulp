Errata Management
========================

The Pulp admin client can be used to install errata on
registered consumers. All errata related commands are found under
the ``consumer errata`` section of the client.

An erratum is metadata communicating an update is available for a
software package.  Errata are typically formed to reflect a security fix,
bug fix, or feature enhancement.  Each erratum refers to a collection of 
updated RPMs.

.. _install-errata:

Install Errata on a Consumer
------------------------------------

Errata are installed through the ``install`` command in the
errata section. Installing a single erratum may equate to updating
multiple RPMs on a consumer.  The install process will examine the
packages currently installed on the consumer and determine if the updated 
RPMs from the erratum apply to the consumer.  A RPM referenced in an 
erratum applies to a consumer if the consumer has as an older version
of that RPM installed.

The following options are available to the errata ``install`` command.
One or more errata may be specified in the same install request. Each erratum is
indicated by an errata id.  In the event that the erratum does not apply to the consumer,
no error is raised and the operation is still marked a success.

Required
^^^^^^^^

``--id``
  Unique identifier for the consumer.

``--errata-id, -e``
  Indicates the id of an erratum to install.  This option may be used multiple
  times to specify multiple erratum. At least one erratum must be specified.

Options
^^^^^^^

``--no-commit``
  If specified, the errata install is to be executed but not committed.
  This option may be used to determine which packages are applicable.

``--import-keys``
  If specified, GPG keys will be imported on the consumer as needed.

``--reboot``
  If sepcified, a reboot will be scheduled on the consumer pending a
  successful transaction containing at least one package change.

