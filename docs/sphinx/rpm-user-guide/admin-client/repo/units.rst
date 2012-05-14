Packages, Errata, and Kickstart Trees
=====================================

.. _copy-packages:

Copy Packages Between Repositories
----------------------------------

Pulp supports the ability to copy packages between repositories. The entire
contents of a repository can be copied or criteria can be specified to select
only a subset of packages. This criteria can revolve around the package metadata,
information about when it was associated to the source repository, or both.

Only the association between the repository and the package is copied. The
package is stored on disk only once and is not duplicated as part of this process.

The criteria used to determine which packages to copy falls under two categories:
package metadata and association metadata. Package metadata refers to fields on
the RPM itself, for example name, version, arch, or description. Association
metadata refers to the time and manner in which it was added to the source
repository, for example the time it was first added to the repository or if
it was added during a sync or manually by a user.

There is a separate command for each type of unit in a repository to be copied
(e.g. rpm v. errata). All of the commands can be found in the ``repo copy``
section of the CLI.

All commands under the copy section require the following arguments:

``--from-repo-id, -f``
  Source repository from which packages will be copied.

``--to-repo-id, -t``
  Destination repository into which packages will be copied. A repository with
  the given ID must already exist before this call.

``--dry-run, -d``
  If specified, a list of the packages that match the given criteria will be
  displayed but the copy is performed. This argument is meant to provide a way
  to verify the packages before committing the change to the server.

The following arguments can be passed to the package related (RPM, SRPM, DRPM)
copy commands. They are divided by the metadata type being matched.

Unit
^^^^

All of the values to the following argument indicate a field in the package's
metadata and the value to match against. The value can be a literal or a
regular expression. For example, to match on a package named "pulp"::

 --match "name=pulp"

An example of matching all packages that start with "p"::

 --match "name=^p.*"

Both arguments and field names may be repeated for more advanced criteria::

 --match "name=pulp.*" --match "name=.*okaara.*" --gte "version=2"

Pulp uses PCRE (Perl-compatible regular expressions) as the regular expression
dialect. More information can be found at `<http://www.pcre.org/pcre.txt>`_.

Valid fields are: name, epoch, version, release, arch,
buildhost, checksum, description, filename, license, and vendor.

``--match``
  Selects packages whose value for the given field matches the specified value.
  Example of selecting only i386 and x86_64 packages: ``--match "arch=i386" --match "arch=x86_64"``

``-not``
  Selects packages whose value for the given field does *not* match the specified
  value. Example of selecting all non-pulp packages in a repository: ``--not "name=^pulp.*"``

``--gt``
  Selects packages whose value for the given field is greater than (but not equal
  to) the specified value. Example of selecting all packages beyond version 1.0: ``--gt "version=1.0"``

``--gte``
  Selects packages whose value for the given field is greater than or equal to
  the specified value. Example of selecting all releases in a 2.x stream: ``--gte "version=2"``

``--lt``
  Selects packages whose value for the given field is less than (but not equal to)
  the specified value.

``--lte``
  Selects packages whose value for the given field is less than or equal to the
  specified value.

Association
^^^^^^^^^^^

The time when the package was first added to the source repository is a
valid criteria option. The following two arguments accept an :term:`iso8601`
timestamp as the value. For example, to copy packages added after May 1st, 2012::

 --after 2012-05-01

``--after``
  Selects packages first added to the source repository on or after the specified
  time.

``--before``
  Selects packages first added to the source repository on or before the specified
  time.

.. _upload-packages:

Uploading Packages Into a Repository
------------------------------------

.. _orphaned-packages:

Orphaned Packages
-----------------

