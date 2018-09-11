Git
===

Pulp source code lives on `GitHub <https://github.com/pulp>`_. The "pulp" repository is for
pulpcore.  This document is definitive for :term:`pulpcore` only, but some plugins may choose to
follow the same strategies.

.. _git-branch:

Versions and Branches
---------------------

Pulp uses a version scheme ``x.y.z``, which is based on `Semantic Versioning
<http://semver.org/>`_. Briefly, ``x.y.z`` releases may only contain bugfixes (no features),
``x.y`` releases may only contain backwards compatible changes (new features, bugfixes), and ``x``
releases may break backwards compatibility.

Most changes should be merged into the ``master`` branch only. When necessary, fixes can be
cherry-picked into ``x.y`` stream.

.. note::

   For additional information on Pulp's branching strategy decision, please
   refer to PUP-0003_

.. _PUP-0003: https://github.com/pulp/pups/blob/master/pup-0003.md


Commits
-------

.. _rebase:

Rebasing and Squashing
**********************

We prefer each pull request to contain a single commit. Before you submit a PR, please consider an
`interactive rebase and squash.
<https://github.com/edx/edx-platform/wiki/How-to-Rebase-a-Pull-Request>`_

The ``git commit --amend`` command is very useful, but be sure that you `understand what it does
<https://www.atlassian.com/git/tutorials/rewriting-history/git-commit--amend>`_ before you use it!
GitHub will update the PR and keep the comments when you force push an amended commit.

.. warning::
   Keep in mind that rebasing creates new commits that are unique from your
   original commits. Thus, if you have three commits and rebase them, you must
   make sure that all copies of those original commits get deleted. Did you push
   your branch to origin? Delete it and re-push after the rebase.

.. _commit-message:

Commit Message
**************

Commit messages in Pulp should contain a human readable explanation of what was fixed.  They should
also follow the standard git message format of starting with a subject line or title (usually
wrapped at about 50 chars) and optionally, a longer message (usually wrapped at 72 characters)
broken up into paragraphs. For more on what constitutes a good commit message, we recommend `Tim
Pope's blog post on the subject
<http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.

Each commit message should reference an issue in `Pulp's Redmine issue tracker
<https://pulp.plan.io>`_. To do this you should **include both a keyword and a link** to the issue.

To reference the issue (but not change its state), use ``re`` or ``ref``::

    re #123
    ref #123

To update the issue's state to MODIFIED and set the %done to 100, use
``fixes`` or ``closes``::

    fixes #123
    closes #123

To reference multiple issues in a commit use a separate line for each one::

    fixes #123
    fixes #124

We strongly suggest that each commit is attached to an issue in Redmine. However, if you must create
a commit for which there is no issue, add the tag ``#noissue`` to the commit's message.

Putting this all together, the following is an example of a good commit message::

    Update node install and quickstart

    The nodes install and quickstart was leaving out an important step on
    the child node to configure the server.conf on the child node.

    closes #1392
    https://pulp.plan.io/issues/1392

You can also reference additional Pull Requests that should be used by Travis
when testing your Pull Request. See :ref:`continuous-integration` for details.
