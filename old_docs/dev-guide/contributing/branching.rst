Branching Model
===============

Pulp lives on `GitHub <https://github.com/pulp>`_. The "pulp" repository is for
the platform, and then each supported content family (like "rpm" and "puppet")
has its own repository.

Pulp uses a version scheme x.y.z. Pulp's branching strategy is designed for
bugfix development for older ``x.y`` release streams without interfering with
development or contribution of new features to a future, unreleased ``x`` or
``x.y`` release. This strategy encourages a clear separation of bugfixes and
features as encouraged by `Semantic Versioning <http://semver.org/>`_.

.. note::

   Pulp's branching model is inspired by the strategy described by Vincent Driessen in
   `this article <http://nvie.com/posts/a-successful-git-branching-model/>`_, but is not
   identical to it.


master
------

This is the latest bleeding-edge code. All new feature work should be done out
of this branch. Typically this is the development branch for future, unreleased
``x`` or ``x.y`` release.


Version-Specific Branches
-------------------------

Each ``x.y`` release will have one corresponding branch called ``x.y-dev``. For
example, all work for the 2.7.z series of releases gets merged into ``2.7-dev``.


Protected Branches
------------------

Within each repository, the ``master`` branch, any branch ending in ``-dev``, and any
branch ending in ``-release`` should be marked as
`protected <https://help.github.com/articles/about-protected-branches/>`_
on GitHub. The basic protection that disallows force-push and deletion is the
only option that should be enabled. There should be no restrictions on required
status checks or who can push. There is a script at
`devel/scripts/protected-branches.py
<https://github.com/pulp/devel/tree/master/scripts/protected-branches.py>`_
that will mark all appropriate branches as protected. Any time new branches are
created that should be protected, that script can be run to do the work.


Build Tags
----------

Builds will be represented only as tags.

.. note:: In the past, the latest beta and GA release of an x.y stream would be
    represented additionally by branches, but that is no longer the case as of
    pulp 2.7.


Build Lifecycle
---------------

Alpha and Beta releases will be built from the tip of an ``x.y-dev`` branch. If
the beta fails testing, blocking issues will have fixes merged to the
``x.y-dev`` branch like any other bug fix, and then a new build will be made.
Other changes unrelated to the blocking issues may get merged to the
``x.y-dev`` branch between builds, and no effort will be made to "freeze" the
branch. Any such unrelated changes will be included in the next beta build.

Release candidates will be built from the most recent beta tag. GA releases
will be built from the most recent release candidate tag.


Hotfix
------

When a hotfix needs to be made, a branch will be created from the most recent
``x.y.z`` release tag. The fix will be made (via pull request from a personal
fork to the hotfix branch), a new tag will be built from the tip of the hotfix
branch, and the hotfix branch can be merged to ``x.y-dev``.

.. _bug_fix_branches:

Bug Fix Branches
----------------

When creating a Pull Request (PR) that fixes a specific bug, title the PR as
you would a :ref:`git commit message <commit_messages>` with a short,
human-readable description. Bug fixes should always be made against
the latest available ``x.y-dev`` branch.


.. _feature_branches:

Feature Branches
----------------

Similar to bug fix branches, the name of a feature branch and its associated
Pull Request should be a short, human-readable description of the feature being added.
For example, a branch to add persistent named searches might be named
``feature/named-searches``. Also new features should go into latest ``x.y-dev`` branch
which does not have corresponding ``x.y-release`` branch. In case there is
no such branch then the ``master`` branch is the right one. If you are not sure
``master`` branch is always the correct one.


.. _choosing-upstream-branch:

Choosing an Upstream Branch
---------------------------

When creating a bug fix or feature branch, it is very important to choose the
right upstream branch. The general rule is to always choose the oldest supported upstream
branch that will need to contain your work. For more info see above
:ref:`Feature Branches <feature_branches>` or :ref:`Bug Fix Branches <bug_fix_branches>`.


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

Putting this altogether, the following is an example of a good commit message::

    Update node install and quickstart

    The nodes install and quickstart was leaving out an important step on
    the child node to configure the server.conf on the child node.

    closes #1392
    https://pulp.plan.io/issues/1392

.. note::
  In case you have multiple commits use ``re`` or ``ref`` in all of them and ``fixes`` or ``close``
  only in the last one to avoid closing the issue before it's completely done.

Cherry-picking and Rebasing
---------------------------

Don't do it! Seriously though, this should not happen between release branches.
It is a good idea (but not required) for a developer to rebase his or her
development branch *before* merging a pull request. Cherry-picking may also
be valuable among development branches. However, master and release branches
should not be involved in either.

The reason is that both of these operations generate new and unique commits from
the same changes. We do not want pulp-x.y and master to have the same bug fix
applied by two different commits. By merging the same commit into both, we can
easily verify months later that a critical bug fix is present in every appropriate
release branch and build tag.

.. note::
 If you are not sure what "rebasing" and "cherry-picking" mean,
 `Pro Git <http://git-scm.com/book>`_ by Scott Chacon is an excellent resource
 for learning about git, including advanced topics such as these.
