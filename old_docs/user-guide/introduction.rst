Introduction
============

Pulp is a platform for managing repositories of content, such as software packages,
and pushing that content out to large numbers of consumers. If you want to locally
mirror all or part of a repository, host your own content in a new repository,
manage content from multiple sources in one place, and push content you choose out
to large numbers of clients in one simple operation, Pulp is for you!

Pulp has a well-documented REST API and command line interface for management.

Pulp is completely free and open-source, and we invite you to join us on GitHub_!

.. _GitHub: https://github.com/pulp

What Pulp Can Do
----------------

* Pull in content from existing repositories to the Pulp server. Do it manually or on a recurring schedule.
* Upload new content to the Pulp server.
* Mix and match uploaded and imported content to create new repositories, then publish and host them with Pulp.
* Publish your content as a web-based repository, to a series of ISOs, or in any other way that meets your needs.
* Push content out to consumer machines, and track what each consumer has installed.

Plugins
-------

Pulp manages content, and its original focus was software packages such as RPMs
and Puppet modules. The core features of Pulp, such as syncing and publishing
repositories, have been implemented in a generic way that can be extended by plugins
to support specific content types. We refer to the core implementation as the **Pulp Platform**.

With this flexible design, Pulp can be extended to manage nearly any type of
digital content.

More importantly, Pulp makes it easy for third-party plugins to be written and
deployed separately from the Pulp Platform. When new plugins are installed, Pulp
detects and activates them automatically.

Goal of this Guide
------------------

Pulp can manage many types of content, but it is not tied to any one of them. As
such, this guide will help you install and configure Pulp, and learn how to use
Pulp's core features in a non-type-specific way. Once you are familiar with what
Pulp can offer, visit the user guide that is specific to the content type in which
you are interested. You can find all of our documentation at `our docs page <http://www.pulpproject.org/docs>`_.

Many examples require the use of a type, and for those we will use "rpm". However,
examples in this guide will only cover features that are common across content types.

.. _platform-support-policy:

Platform Support Policy
-----------------------

CentOS/Red Hat Enterprise Linux (RHEL)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Pulp team aims to provide RPM builds for the last two major releases of RHEL. For
example, if the latest version is RHEL 8, builds should be available for RHEL 8 and
RHEL 7. However, due to the long life cycle of these platforms and the relatively rapid
development cycle of both Pulp and its dependencies, we may need to stop supporting
the older platform before the next major release of RHEL. If this does occur, announcements
will be made well in advance.

.. note::
  It is likely that support for Red Hat Enterprise Linux 6 will be removed prior to
  the release of Red Hat Enterprise Linux 8. This is due to the difficulty of
  supporting both Python 2.6 and Python 3 at the same time.

Currently we support Red Hat Enterprise Linux 6 and 7 as well as CentOS 6 and 7.


Fedora
^^^^^^

Pulp follows the `Fedora release life cycle
<https://fedoraproject.org/wiki/Fedora_Release_Life_Cycle#Maintenance_Schedule>`_.
This means that when a release of Fedora reaches its End of Life, Pulp will no longer
support that platform in any way, including providing updates for any security
vulnerabilities.
