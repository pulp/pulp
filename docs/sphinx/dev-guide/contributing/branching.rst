Branching Model
===============

Pulp lives on `GitHub <https://github.com/pulp>`_. The "pulp" repository is for
the platform, and then each supported content family (like "rpm" and "puppet")
has its own repository.

master
------

This is the latest bleeding-edge code.


Release Branches
----------------

Pulp uses a version scheme x.y.z. A branch will be made for each x.y named
"pulp-x.y". For example, the 2.0 release lives in a branch named "pulp-2.0".


Bug Fix Branches
----------------

A bug fix branch name should contain the developer's username and a Bugzilla bug
number, separated by a hyphen. For example, "mhrivnak-876543".


Feature Branches
----------------

Similar to bug fix branches, the name of a feature branch should usually be the
developer's username plus a brief name relevant to the feature. For example,
a branch to add persistent named searches might be named "mhrivnak-named-searches".

In a case where multiple developers will contribute to a feature branch, simply
omit the username and call it "named-searches".


Choosing an Upstream Branch
---------------------------

When creating a bug fix or feature branch, it is very important to choose the
right upstream branch. The general rule is to always choose the oldest upstream
branch that will need to contain your work.

For example, if your work needs to go in versions 2.0, 2.1 and 2.2 alpha, you
would create your branch from the 2.0 branch. After making some commits, merge
your branch into each of the release branches.


Cherry-picking and Rebasing
---------------------------

Don't do it! Seriously though, this should not happen between release branches.
It is a good idea for a developer to rebase his or her development branch *before*
submitting a pull request. Cherry-picking may also be valuable among development
branches. However, master and release branches should not be involved in either.

The reason is that both of these operations generate new and unique commits from
the same changes. We do not want pulp-x.y and master to have the same bug fix
applied by two different commits. By merging the same commit into both, we can
easily verify months later that a critical bug fix is present in every appropriate
release branch and build tag.

