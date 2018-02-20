Pull Request Walkthrough
========================

Changes are submitted via Pull Requests TODO(link, github definition) to the TODO(link, pulp/pulp)
repository. Plugin repositories are listed on the TODO(link, plugin table). This page

Working with Git
----------------

The Pulp project uses TODO(link, git)

Describe here, link to PUP 3

* 3.0-dev
* from master to master

Feature branches

Rebase and Squash
*****************

Commit Messages
***************

Commit messages in Pulp should contain a human readable explanation of what
was fixed in the commit. They should also follow the standard git message
format of starting with a subject line or title (usually wrapped at about 50
chars) and optionally, a longer message (usually wrapped at 72 characters)
broken up into paragraphs. For more on what constitutes a good commit message,
we recommend `Tim Pope's blog post on the subject
<http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.

It's also recommended that every commit message in Pulp reference an issue in
`Pulp's Redmine issue tracker <https://pulp.plan.io>`_. To do this you should
use both a keyword and a link to the issue.

To reference the issue (but not change its state), use ``re`` or ``ref``::

    re #123
    ref #123

To update the issue's state to MODIFIED and set the %done to 100, use
``fixes`` or ``closes``::

    fixes #123
    closes #123

You can also reference multiple issues in a commit::

    fixes #123, #124

Putting this all together, the following is an example of a good commit message::

    Update node install and quickstart

    The nodes install and quickstart was leaving out an important step on
    the child node to configure the server.conf on the child node.

    closes #1392
    https://pulp.plan.io/issues/1392
Commit message <link to style_guide/commitmessage>

Testing
-------

Style Guide
-----------
link

Documentation
-------------

If a change affects the user experience, please update the documentation. Documentation changes
should be included in the Pull Request that adds/updates a feature.

link contributing/documentation

Open a PR on GitHub
-------------------
