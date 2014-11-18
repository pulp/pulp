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

All example commands should begin with only ``$ `` as a prompt. Commands that
must be run as root should be shown using ``sudo``.

Docs Layout
-----------

Relative to the root of pulp, the user guide is stored at ``dev/sphinx/user-guide/``
and the dev guide is stored at ``docs/sphinx/dev-guide/``.


Read the Docs
-------------

Pulp's documentation is hosted on `Read the Docs <http://readthedocs.org>`_.
Links to all current documentation can be found at
`http://www.pulpproject.org/docs <http://www.pulpproject.org/docs>`_.


RTD Versions
------------

When viewing docs on Read the Docs, there are multiple versions linked in the
bottom-left corner of the page. Past releases each have a link named "pulp-x.y"
and are built from the most recent commit on the corresponding "pulp-x.y"
release branch. Documentation shown on Read the Docs must be merged onto the
appropriate branch for it to be displayed. The "latest" version corresponds
to the most recently released version of Pulp.

Docs automatically get built when a commit happens to a corresponding branch.
However, it seems that builds may not happen automatically when only a merge
takes place.

   .. note::

      You can manually start a build on Read the Docs for a specific version
      using the `user guide build page <https://readthedocs.org/builds/pulp-user-guide/>`_
      or the `dev guide build page <https://readthedocs.org/builds/pulp-dev-guide/>`_.

There may be a "staging" version at times. This build is used by the team to
share documentation that has not yet been reviewed.

Editing the Docs
-----------------

The Pulp docs support `intersphinx <http://sphinx-doc.org/ext/intersphinx.html>`_
and `extlinks <http://sphinx-doc.org/ext/extlinks.html>`_.

To refer to a document in a plugin or platform, you can do something like so:::

     :ref:`installation <platform:server_installation>`

This will create a link to the correct reference in the platform docs.

You can use the extlinks extension to create links to bugzilla. For example:::

     :bz:`123456`

Will create a link like this: :bz:`123456`. There is also a ``:fixedbugs:``
directive to find all bugs related to a particular version of Pulp. This is
useful in release notes.


Building the Docs
-----------------

Anyone can build the docs in their own dev environment, which is useful for
proofing changes to the docs before committing them. For either the user guide
or the dev guide, navigate to the base docs folder and run ``make html``. Once
run, the html is available in ``_build/html``.

The html is built with the vanilla sphinx theme, so the look and feel is
different than Read the Docs look and feel.

You do not need to clean the docs before rebuilding. If you do need to
clean the docs, you should run ``make clean`` from the documentation root.
