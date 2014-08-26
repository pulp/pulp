Branching Model
===============

Pulp lives on `GitHub <https://github.com/pulp>`_. The "pulp" repository is for
the platform, and then each supported content family (like "rpm" and "puppet")
has its own repository.

Pulp uses a version scheme x.y.z. Pulp's branching strategy is designed for
development of bugfixes for older "x.y" release streams without interfering with
development or contribution of new features for "x" and "x.y" releases.


master
------

This is the latest bleeding-edge code. All new feature work should be done out
of this branch. Typically this is the development branch for "x" and "x.y"
releases.


Release Branches
----------------

A branch will be made for each x.y release stream named "pulp-x.y". For example,
the 2.0 release lives in a branch named "pulp-2.0". Increments of "z" releases
occur within the same release branch and are identified by tags.

The HEAD of each release branch points to a tagged release version. When a new
"z" increment version of Pulp is released, the development branch is merged
into the release branch and the new HEAD is tagged. Development occurs on a
separate development branch as described below.


Development Branches
--------------------

Development for future "z" releases are done in a corresponding branch named
"x.y-dev". For example, assuming Pulp 2.4.0 is released on the branch
"pulp-2.4", development of 2.4.1 will occur on a branch named "2.4-dev". When
2.4.1 is ready to be released, it will be merged with the pulp-2.4 branch at
which point "2.4-dev" will be used for 2.4.2 development.


Bug Fix Branches
----------------

When creating a pull request that fixes a specific bug in bugzilla, a naming
convention is used for the pull request branch that is merged with the
development branch. A bugzilla bug fix branch name should contain the
developer's username and a Bugzilla bug number, separated by a hyphen. For
example, "mhrivnak-876543". Optionally, a short description may follow the BZ
number.


Feature Branches
----------------

Similar to bug fix branches, when creating a pull request that holds features
until they are merged into a development branch, the pull request branch should
be the developer's username plus a brief name relevant to the feature. For
example, a branch to add persistent named searches might be named
"mhrivnak-named-searches".

In a case where multiple developers will contribute to a feature branch, simply
omit the username and call it "named-searches".


.. _choosing-upstream-branch:

Choosing an Upstream Branch
---------------------------

When creating a bug fix or feature branch, it is very important to choose the
right upstream branch. The general rule is to always choose the oldest upstream
branch that will need to contain your work.


Merging Forward
---------------

After choosing your upstream branch to merge your changes into and performing
that merge, you additionally need to merge forward your commit to all "newer"
branches.

For example, if your work needs to go in versions 2.0, 2.1 and 2.2 alpha, you
would create your branch from the 2.0 branch. After making some commits, merge
your branch into each of the release branches. Merging forward includes merging
all the way to master. Master is used for the largest feature changes which
later get merged as a "x" or "y" release, so by merging forward now, merge
conflicts can be avoided later.


Cherry-picking and Rebasing
---------------------------

Don't do it! Seriously though, this should not happen between release branches.
It is a good idea (but not required) for a developer to rebase his or her
development branch *before* submitting a pull request. Cherry-picking may also
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
