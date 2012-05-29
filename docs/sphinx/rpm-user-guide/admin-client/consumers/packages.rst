Consumer Package Management
===========================

Install Packages on a Consumer
------------------------------

Packages (RPM) are installed through the ``consumer package`` command.

The following options are available to the package install command.  One or more
packages may be specified for install.  Each package name may be just the name component
of the NEVRA, or may contain all or some other components.  No error is raised when any
of the specified packages are already installed.

Basic
^^^^^

``--id``
  Unique identifier for the consumer. Valid characters include letters,
  numbers, hyphen (``-``) and underscore (``_``). The ID is case sensitive;
  "pulp" and "Pulp" are two separate consumers. An ID is required.

``--name, -n``
  A package name.  This may be just the name component of the NEVRA, or may
  contain all or some other components.  This option may be used multiple
  times to specify multiple packages.  At least (1) package must be specified.

Options
^^^^^^^

``--no-commit``
  A flag that indicates that the package install is to be executed but not
  committed.  This option is useful for users to see how package names will be
  resolved and any dependancies that also be installed.

``--import-keys``
  A flag that indicates that GPG keys may be imported as needed.

``--reboot``
  A flag that indicates that a consumer reboot should be scheduled pending
  the successful install of at least (1) package.

Uninstall Packages on a Consumer
--------------------------------

Packages (RPM) are uninstalled through the ``consumer package`` command.

The following options are available to the package uninstall command.  One or more
packages may be specified for uninstall.  Each package name may be just the name component
of the NEVRA, or may contain all or some other components.  No error is raised when any
of the specified packages are not installed.

Basic
^^^^^

``--id``
  Unique identifier for the consumer. Valid characters include letters,
  numbers, hyphen (``-``) and underscore (``_``). The ID is case sensitive;
  "pulp" and "Pulp" are two separate consumers. An ID is required.

``--name, -n``
  A package name.  This may be just the name component of the NEVRA, or may
  contain all or some other components.  This option may be used multiple
  times to specify multiple packages.  At least (1) package must be specified.

Options
^^^^^^^

``--no-commit``
  A flag that indicates that the package uninstall is to be executed but not
  committed.  This option is useful for users to see how package names will be
  resolved and any dependancies that also be uninstalled.

``--reboot``
  A flag that indicates that a consumer reboot should be scheduled pending
  the successful uninstall of at least (1) package.

Update Packages on a Consumer
-----------------------------

Packages (RPM) are updated through the ``consumer package`` command.

The following options are available to the package update command.  One or more
packages may be specified for update.  Each package name may be just the name component
of the NEVRA, or may contain all or some other components.  No error is raised when any
of the specified packages are already updated.

Basic
^^^^^

``--id``
  Unique identifier for the consumer. Valid characters include letters,
  numbers, hyphen (``-``) and underscore (``_``). The ID is case sensitive;
  "pulp" and "Pulp" are two separate consumers. An ID is required.

``--name, -n``
  A package name.  This may be just the name component of the NEVRA, or may
  contain all or some other components.  This option may be used multiple
  times to specify multiple packages.  To specify that ALL packages are to
  be updated, omit this option.

Options
^^^^^^^

``--all, -a``
  A flag that confirms that not specifying any packages to be updated
  implies that ALL packages are to be updated.  Required, when no packages
  are specified.

``--no-commit``
  A flag that indicates that the package update is to be executed but not
  committed.  This option is useful for users to see how package names will be
  resolved and any dependancies that also be updated.

``--import-keys``
  A flag that indicates that GPG keys may be imported as needed.

``--reboot``
  A flag that indicates that a consumer reboot should be scheduled pending
  the successful update of at least (1) package.