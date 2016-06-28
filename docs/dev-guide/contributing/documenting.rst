Creating Documentation
======================

Platform vs. Type-Specific User Guides
--------------------------------------

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

All example commands should begin with only ``$`` as a prompt. Commands that
must be run as root should be shown using ``sudo``.

Docs Layout
-----------

Platform and plugins each have their own Sphinx project which allow docs to be
built without checking out additional repositories. The Sphinx project for
platform and each plugin are located in the ``docs`` directory in the top level
of the repository. For example, the platform Sphinx project
`is located here <https://github.com/pulp/pulp/tree/master/docs>`_.

Doc Hosting
-----------

Pulp's documentation is hosted on `OpenShift <https://www.openshift.com/>`_.
and is available at `https://docs.pulpproject.org/ <https://docs.pulpproject.org/>`_.

Doc Versions
------------

The current, stable GA release are hosted at https://docs.pulpproject.org/

GA releases for version X.Y are hosted at https://docs.pulpproject.org/en/X.Y/

A given X.Y version could have either a Beta or an RC but not both, so
those are hosted at the same place https://docs.pulpproject.org/en/X.Y/testing/

Nightly docs for a given X.Y release are hosted at https://docs.pulpproject.org/en/X.Y/nightly/

Old doc versions not available on https://docs.pulpproject.org/ are available via source.

Editing the Docs
----------------

The Pulp docs support `extlinks <http://sphinx-doc.org/ext/extlinks.html>`_.

Use the ``:redmine:`` directive to easily create links to Pulp issues. For
example::

     :redmine:`123`

Creates a link to issue 123 like this: :redmine:`123`. You can also set the
text for the link using this syntax::

     :redmine:`my new link text <123>`

Which creates this link: :redmine:`my new link text <123>` There is also a
``:fixedbugs:`` directive to link to all bugs for a specific version of Pulp.
This is useful in release notes. For example::

     :fixedbugs:`2.6.0`

Create a link to bugs fixed in 2.6.0 like this: :fixedbugs:`2.6.0`. This can
have its link text set using the syntax::

     :fixedbugs:`these great bugs were fixed <2.6.0>`

Which creates this link: :fixedbugs:`these great bugs were fixed <2.6.0>`

Build Docs Locally
------------------

Building docs locally is easy::

    1. Navigate to the Sphinx project folder
    2. ``make html``
    3. Browse the docs the folder ``docs/_build/html``.

The Vagrant environment comes pre-loaded with all the dependencies you need
to build the docs.

If the Python environment you build the docs in has the ``sphinx_rtd_theme``
Python package, the docs will have the same look and feel as
`https://docs.pulpproject.org/ <https://docs.pulpproject.org/>`_. If not,
you will get the default Sphinx theme. Either should be sufficient for
proofing content changes.

You do not need to clean the docs before rebuilding. If you do need to
clean the docs, you should run ``make clean`` from the documentation root.

Build Docs for docs.pulpproject.org
-----------------------------------

Nightly docs are built automatically each night. If builds fail,
e-mail is sent to the docs maintainers who are expected to resolve issues.

GA, RC, and Beta docs are triggered manually as part of the release process.

See all of the `Jenkins doc builders <https://pulp-jenkins.rhev-ci-vms.eng.
rdu2.redhat.com/view/Docs%20Builders/>`_.