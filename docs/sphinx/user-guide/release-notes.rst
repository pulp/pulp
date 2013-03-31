=============
Release Notes
=============

Pulp 2.1.0
==========

New Features
------------

#. Pulp now has support for heirarchichal collections of Pulp Servers that are able to synchronize with each
   other. This is called Pulp Nodes, and you can read more about them :doc:`nodes`.
#. Unit counts are now tracked by type.
#. We now support Fedora 18 and Apache 2.4.
#. The ``pulp-admin rpm consumer [list, search, update, unregister, history]`` commands from the pulp_rpm
   project have been moved into this project, and can now be found under ``pulp-admin consumer *``.

Note of Caution
---------------

The pulp-consumer bind and unbind operations have been moved out of this project into the pulp_rpm project.
If you install pulp-rpm-consumer-extensions, you will find these operations under pulp-consumer rpm
{bind,unbind}.

Noteworthy Bugs Fixed
---------------------

`872724 <https://bugzilla.redhat.com/show_bug.cgi?id=872724>`_ - Requesting package profile on consumer without
a package profile results in error

`878234 <https://bugzilla.redhat.com/show_bug.cgi?id=878234>`_ - Consumer group package_install, update and
uninstall not returning correct result

`916794 <https://bugzilla.redhat.com/show_bug.cgi?id=916794>`_ - pulp-admin orphan list, Performance & Memory
concerns (~17 minutes and consuming consuming ~1.65GB memory). The --summary flag was removed and summary
behavior was made the default when listing orphans. A new --details flag has been added to get the previous
behavior.

`918160 <https://bugzilla.redhat.com/show_bug.cgi?id=918160>`_ - Orphan list --summary mode isn't a summary.
Listing orphans now returns a much smaller set of related fields (namely only the unit keys).

`920792 <https://bugzilla.redhat.com/show_bug.cgi?id=920792>`_ - High memory usage (growth of 2GB) from orphan
remove --all. All server-side orphan operations now use generators instead of database batch queries.

RFE Bug
-------

`876725 <https://bugzilla.redhat.com/show_bug.cgi?id=876725>`_ - RFE - consumer/agent - support option to
perform 'best effort' install of content. We will now avoid aborting an install when one of the packages is not
available for installation.

API Changes
-----------

Applicability API Changes
^^^^^^^^^^^^^^^^^^^^^^^^^

We have improved Content Applicability API significantly in this release. A few major enhancements are:
 
#. Added an optional ``repo_criteria`` parameter to be able to specify repositories to restrict the
   applicability search to.
#. Changed input type of units to be a dictionary keyed by Content Type ID and a list of units of that type as a
   value. You can also pass in an empty list corresponding to a Content Type ID to check the applicability of
   all units of that specific type.
#. All 3 parameters are now optional. Check out updated API documentation to read more about the behavior of the
   API in case of missing parameters.
#. Return format is updated to a more compact format keyed by Consumer ID and Content Type ID and it now returns
   only applicable units.

The API is documented in detail 
`here <http://pulp-dev-guide.readthedocs.org/en/devguide-2.1/integration/rest-api/consumer/applicability.html>`_.

Distributor Plugin API Change
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Distributor plugin method ``create_consumer_payload`` has changed to accept a new parameter,
``binding_config``. Individual bindings can contain configuration options that may be necessary when providing
the consumer with the information necessary to use the published repository. This field will contain those
options if specified by the user.

Upgrade Instructions
--------------------

To upgrade to the new Pulp release, you should begin by using yum to install the latest RPMs from the Pulp
repository, run the database migrations, and cleanup orphaned packages::

    $ sudo yum upgrade
    $ sudo pulp-manage-db
    $ sudo pulp-admin orphan remove --all
