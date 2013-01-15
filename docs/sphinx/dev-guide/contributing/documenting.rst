Creating Documentation
======================

Platform vs. Type-Specific User Guides
------------------------------

The platform user guide should cover all generic features of Pulp. When examples
are appropriate, it should use the "rpm" content type, but only utilize features
that are generic across content types.

User guides for content types should avoid repeating what is already in the
platform guide and instead focus on these two topics:

1. What new features does this content type provide? For example, RPM support
   includes protected repos.

2. Create a quick-start guide that shows examples of how to do the most basic
   and interesting operations. For example, create a repository, sync it, and
   publish it. Show more advanced stories as "recipes".


Command Line User Guide
-----------------------

Our command line tools such as ``pulp-admin`` and ``pulp-consumer`` do a very
good job of self-documenting with help text. Pulp's user guides should not
duplicate this information. Enumerating every flag and option of the CLI tools
would leave us with two places to maintain the same documentation, which would
inevitably go out of sync.

The user guides should instead add value beyond what the CLI tools can
self-document. Focus on how to use specific features, show lots of examples, and
keep in mind what use cases users are likely to be interested in.

Examples should not include long lines that will require horizontal scrolling.

All example commands should begin with only ``$ `` as a prompt. Commands that
must be run as root should be shown using ``sudo``.


Read the Docs
-------------

Pulp's documentation is hosted on `Read the Docs <http://readthedocs.org>`_.
Links to all current documentation can be found at
`http://www.pulpproject.org/docs <http://www.pulpproject.org/docs>`_.


RTD Versions
------------

When viewing docs on Read the Docs, there are multiple versions linked in the
upper-left corner of the page. The "latest" version corresponds to the version
of Pulp currently under development. Past releases each have a link named
"pulp-x.y".

There may be a "staging" version at times. This build is used by the team to
share documentation that has not yet been reviewed.


Building the Docs
-----------------

Anyone can induce a build of Pulp's documentation on Read the Docs. When viewing
the docs, click the icon in the bottom-right corner of the page. This brings you
to a page where you can select a version and build it.

This will not generally be necessary, as the docs automatically get built when
a commit happens to a corresponding branch. However, it seems that builds may
not happen automatically when only a merge takes place.
