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


Bug Fix Branches
----------------

When creating a Pull Request (PR) that fixes a specific bug, title the PR as
you would the :ref:`git commit message <commit_messages>`.


Feature Branches
----------------

Similar to bug fix branches, when creating a pull request that holds features
until they are merged into a development branch, the pull request branch should
be a brief name relevant to the feature. For example, a branch to add persistent
named searches might be named "feature/named-searches".


.. _choosing-upstream-branch:

Choosing an Upstream Branch
---------------------------

When creating a bug fix or feature branch, it is very important to choose the
right upstream branch. The general rule is to always choose the oldest upstream
branch that will need to contain your work.

.. _commit_messages:

Commit Messages
---------------

The primary commit in a bug fix should have a log message that starts with
'<bug_id> - ', for example ``123456 - fixes a silly bug``.


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
