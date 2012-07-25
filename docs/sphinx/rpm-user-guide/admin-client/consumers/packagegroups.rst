Package Group Management
========================

The Pulp admin client can be used to manipulate installed package groups on
registered consumers. All package group related commands are found under
the ``consumer package-group`` section of the client.

.. _install-package-group:

Install Package Groups on a Consumer
------------------------------------

Package groups are installed through the ``install`` command in the
package-group section.  Package groups are collections of packages (RPMs).
Installing a group is simply a short hand for installing the packages by name.
As such, the group is considered to be installed on a consumer when all of the
packages associated with the group are installed.  The group itself is not part
of the consumer's content inventory.

The following options are available to the package group ``install`` command.
One or more groups may be specified in the same install request. Each group is
indicated by name.  In the event that all packages associated with a group are
already installed, no error is raised and the operation is still marked a success.

Basic
^^^^^

``--id``
  Unique identifier for the consumer.

``--name, -n``
  Indicates the name of a group to install.  This option may be used multiple
  times to specify multiple groups. At least one group must be specified.

Options
^^^^^^^

``--no-commit``
  If specified, the group install is to be executed but not committed.
  This option may be used to see how package names will be resolved and any
  dependencies that will be installed as well.

``--import-keys``
  If specified, GPG keys will be imported on the consumer as needed.

``--reboot``
  If sepcified, a reboot will be scheduled on the consumer pending a
  successful transaction containing at least one package change.

Uninstall Package Groups on a Consumer
--------------------------------------

Package groups are uninstalled through the ``uninstall`` command in the
``package-group`` section.

See :ref:`install-package-group` for more information on arguments to this command.
All install arguments with the exception of ``import-keys`` are supported by
the ``uninstall`` command.
