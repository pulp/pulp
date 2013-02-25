Versioning
==========

This version policy closely follows the
`Semantic Versioning <http://semver.org/>`_ model. Formatting of pre-release
designations and build information does not exactly follow the Semantic
Versioning model, but instead follows established standards for Python and RPM
packaging.


Python Package Version
----------------------

The version of Pulp's Python packages should follow the
`PEP-386 <http://www.python.org/dev/peps/pep-0386/>`_ scheme for
setuptools utilizing a "X.Y.Z" pattern as major, minor and patch versions
respectively.

Alpha, beta, and release candidate versions will be designated by a single
character "a", "b" or "c" after the patch number, for example "2.1.0a".

Pulp is not currently distributed as Python packages, but instead as RPM
packages. Thus, there may not be an effort to distinguish between different
versions of an alpha, beta or release candidate. Instead, the version is likely
to stay at something like "2.1.0a" for some period of time before moving to
"2.1.0b", etc. Put another way, pre-release version numbers may not be incremented
regularly.


RPM Package Version
-------------------

Pulp's RPM packages should follow the version scheme
`prescribed by Fedora <http://fedoraproject.org/wiki/Packaging:NamingGuidelines#Package_Versioning>`_.

This scheme is very similar to the Python version scheme, except the pre-release
designations go in the release field.

For all pre-release versions, the first item of the "release" field will be "0".
The second item will increment with each build. The third item will be one of
"alpha", "beta", and "rc".

For each released version, the "release" field will begin at "1" and increment
with new builds of the same version.


Lifecycle Example
-----------------

=================== ========    =====
      Stage          Python      RPM
=================== ========    =====
Release             2.0.0       2.0.0-1
New Build           2.0.0       2.0.0-2
Bug Fix Beta        2.0.1b      2.0.1-0.1.beta
Bug Fix Release     2.0.1       2.0.1-1
Begin Minor Release 2.1.0a      2.1.0-0.1.alpha
More Work           2.1.0a      2.1.0-0.2.alpha
Feature Complete    2.1.0b      2.1.0-0.3.beta
More Work           2.1.0b      2.1.0-0.4.beta
Release Candidate   2.1.0c      2.1.0-0.5.rc
Release Candidate   2.1.0c      2.1.0-0.6.rc
Release             2.1.0       2.1.0-1
=================== ========    =====
