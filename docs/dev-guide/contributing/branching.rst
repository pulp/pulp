Branching Model
===============

Pulp lives on `GitHub <https://github.com/pulp>`_. The "pulp" repository is for
the platform, and then each supported content family (like "rpm" and "puppet")
has its own repository.

Pulp uses a version scheme ``x.y.z``. Pulp's branching strategy is designed for
bugfix development on the ``2-master`` branch with cherry-picking fixes into
``x.y`` streams as necessary. This version scheme is based
on the `Semantic Versioning <http://semver.org/>`_ strategy.

.. note::

   For additional information on Pulp's branching strategy decision, please
   refer to PUP-0003_

.. _PUP-0003: https://github.com/pulp/pups/blob/master/pup-0003.md

2-master
--------

This is the latest bleeding-edge code. All work should be done out of this branch.


Version-Specific Branches
-------------------------

Each ``x.y`` release will have one corresponding branch called ``x.y-release``.  Fixes
are cherry-picked back to these branches for each ``x.y.z`` release.


Protected Branches
------------------

Within each repository, the ``master`` branch, and any branch ending in ``-release``
should be marked as
`protected <https://help.github.com/articles/about-protected-branches/>`_
on GitHub. The basic protection that disallows force-push and deletion is the
only option that should be enabled. There should be no restrictions on required
status checks or who can push. There is a script at
`devel/scripts/protected-branches.py
<https://github.com/pulp/devel/blob/2-master/scripts/protect-branches.py>`_
that will mark all appropriate branches as protected. Any time new branches are
created that should be protected, that script can be run to do the work.


Build Tags
----------

Builds will be represented only as tags.

.. note:: In the past, the latest beta and GA release of an ``x.y`` stream would be
    represented additionally by branches, but that is no longer the case as of
    pulp 2.7.


Build Lifecycle
---------------

Alpha and Beta releases will be built from the tip of an ``x.y-release`` branch. If
the beta fails testing, blocking issues will have fixes merged to the 2-master branch
and picked back to the ``x.y-release`` branch like any other bug fix, and then a new
build will be made.

Release candidates will be built from the most recent beta tag. GA releases
will be built from the most recent release candidate tag.


Hotfix
------

When a hotfix needs to be made. The fix will be made (via pull request from a personal
fork to the ``x.y-release`` branch), a new tag will be built from the tip of the
branch, and the fix can be cherry-picked forward with a pull request to ``2-master``.

.. _bug_fix_branches:

Bug Fix Branches
----------------

When creating a Pull Request (PR) that fixes a specific bug, title the PR as
you would a :ref:`git commit message <commit_messages>` with a short,
human-readable description. Bug fixes should always be made against
the ``2-master`` branch.


.. _feature_branches:

Feature Branches
----------------

Similar to bug fix branches, the name of a feature branch and its associated
Pull Request should be a short, human-readable description of the feature being added.
For example, a branch to add persistent named searches might be named
``feature/named-searches``. New features should go into the ``2-master`` branch.


.. _choosing-upstream-branch:

Choosing an Upstream Branch
---------------------------

When creating a bug fix or feature branch, it is very important to choose the
right upstream branch. The general rule is to always choose the ``2-master`` branch.
For more info see above :ref:`Feature Branches <feature_branches>` or
:ref:`Bug Fix Branches <bug_fix_branches>`.


.. _naming-of-the-new-branch:

Naming of the new Branch
------------------------

It is advised to use the number of your issue or story when you are creating your new branch name.
Some examples of naming:

  * Issue #2524 - Vagrant enviroment is not starting properly => ``2524-vagrant-init-fix``
  * Story #2523 - Implement regex upload of packages => ``2523-regex-upload``

.. _commit_messages:

Commit Messages
---------------

Commit messages in Pulp should contain a human readable explanation of what
was fixed in the commit. They should also follow the standard git message
format of starting with a subject line or title (usually wrapped at about 50
chars) and optionally, a longer message (usually wrapped at 72 characters)
broken up into paragraphs. For more on what constitutes a good commit message,
we recommend `Tim Pope's blog post on the subject
<http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.

It's also recommended that every commit message in Pulp reference an issue in
Pulp's Redmine_ issue tracker. To do this you should use both a keyword and a
link to the issue.

To reference the issue (but not change its state), use ``re`` or ``ref``::

    re #123
    ref #123

To update the issue's state to MODIFIED and set the %done to 100, use
``fixes`` or ``closes``::

    fixes #123
    closes #123

You can also reference multiple issues in a commit::

    fixes #123, #124

Putting this altogether, the following is an example of a good commit message::

    Update node install and quickstart

    The nodes install and quickstart was leaving out an important step on
    the child node to configure the server.conf on the child node.

    closes #1392
    https://pulp.plan.io/issues/1392

.. note::
  In case you have multiple commits use ``re`` or ``ref`` in all of them and ``fixes`` or ``close``
  only in the last one to avoid closing the issue before it's completely done.


.. _Redmine: https://pulp.plan.io

Rebasing
--------

Don't do it! Seriously though, this should not happen between release branches.
It is a good idea (but not required) for a developer to rebase his or her
development branch *before* merging a pull request.

.. note::
 If you are not sure what "rebasing" means,
 `Pro Git <http://git-scm.com/book>`_ by Scott Chacon is an excellent resource
 for learning about git, including advanced topics such as these.
