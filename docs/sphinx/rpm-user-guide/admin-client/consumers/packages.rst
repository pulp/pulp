Consumer Package Management
===========================

The Pulp admin client can be used to manipulate installed packages on registered
consumers. All package-related commands are found under the ``consumer package``
section of the client.

.. _install-packages:

Install Packages on a Consumer
------------------------------

Packages (RPMs) are installed through the ``install`` command in the packages
section.

The following options are available to the package install command. One or more
packages may be specified in a given install request. Each package is indicated
by a subset of the package's NEVRA, the simplest approach being to simply specify
the name of the package. In the event a package is already installed, no error
is raised and the operation is still marked a success.

Basic
^^^^^

``--id``
  Unique identifier for the consumer. Valid characters include letters,
  numbers, hyphen (``-``) and underscore (``_``). The ID is case sensitive;
  "pulp" and "Pulp" are two separate consumers. An ID is required.

``--name, -n``
  Indicates a package to install. This may be just the name component of the NEVRA
  or may contain other components of the NEVRA. This option may be used multiple
  times to specify multiple packages. At least one package must be specified.

Options
^^^^^^^

``--no-commit``
  A flag that indicates that the package install is to be executed but not
  committed. This option is useful to see how package names will be
  resolved and any dependencies that be installed as well.

``--import-keys``
  If specified, GPG keys may be imported on the consumer as needed.

``--reboot``
  A flag that indicates that a consumer reboot should be scheduled pending
  the successful install of at least one requested package.

Uninstall Packages on a Consumer
--------------------------------

Packages are uninstalled through the ``uninstall`` command in the packages section.

See :ref:`install-packages` for more information on arguments to this command.
All install arguments with the exception of ``import-keys`` are supported by
the uninstall command.

Update Packages on a Consumer
-----------------------------

The ``update`` command in the packages section can be used to update packages
installed on a consumer.

See :ref:`install-packages` for more information on arguments to this command.
The only additional argument is as follows:

``--all, -a``
  If specified, the consumer is requested to update *all* of its  packages.
  This value is required when no packages are specified using the ``name``
  argument.
