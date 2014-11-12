Branching Model
===============

Pulp lives on `GitHub <https://github.com/pulp>`_. The "pulp" repository is for
the platform, and then each supported content family (like "rpm" and "puppet")
has its own repository.

Pulp uses a version scheme x.y.z. Pulp's branching strategy is designed for
bugfix development for older "x.y" release streams without interfering with
development or contribution of new features to a future, unreleased "x" or
"x.y" release. This strategy encourages a clear separation of bugfixes and
features as encouraged by `Semantic Versioning` <http://semver.org/>`_.


master
------

This is the latest bleeding-edge code. All new feature work should be done out
of this branch. Typically this is the development branch for future, unreleased
"x" or "x.y" release.


Release Branches
----------------

A branch will be made for each x.y release stream named "x.y-release". For example,
the 2.4 release lives in a branch named "2.4-release". Increments of "z" releases
occur within the same release branch and are identified by tags.

The HEAD of each release branch points to a tagged release version. When a new
"z" increment version of Pulp is released, the testing branch is merged
into the release branch and the new HEAD of the release branch is tagged.
Development occurs on a separate development branch.

Release branches are where Read The Docs builds from, so in some situations
documentation commits may be merged into a release branch after a release has
occurred. For example if a known issue is discovered in a release after it is
released, it may be added to the release notes. In those situations the
release tag will stay the same and diverge from HEAD.


Testing Branches
----------------

Each x.y release will also have a branch for testing builds named "x.y-testing". For example, the
2.4 stream has a "2.4-testing" branch. This branch is made when we are ready to begin regression
testing 2.4.1. After 2.4.0 has been released, the 2.4-dev branch will be merged into 2.4-testing,
and this branch will be used to make beta builds. Release candidates will also be built out of this
branch. Once we believe the 2.4-testing branch has code that is ready to be release, it will be
merged into 2.4-release.


Development Branches
--------------------

Development for future "z" releases are done in a corresponding branch named
"x.y-dev". For example, assuming Pulp 2.4.0 is released on the branch
"2.4-release" and 2.4.1 is being tested in "2.4-testing", 2.4.2 work will be developed in 2.4-dev.
When 2.4.2 is ready to be beta tested, 2.4-dev will be merged into the "2.4-testing" branch at
which point "2.4-dev" will be used for 2.4.3 development.


Bug Fix Branches
----------------

When creating a pull request that fixes a specific bug in bugzilla, a naming
convention is used for the pull request branch that is merged with the
development branch. A bugzilla bug fix branch name should contain
the bugzilla bug number and optionally, a short description may follow the BZ
number.


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

After choosing your upstream branch to merge your changes into and performing
that merge, you additionally need to merge forward your commit to all "newer"
branches. See :ref:`Merging to Multiple Releases <merging-to-multiple-releases>`
for more information on merging forward from an older branch.

Commit Messages
---------------

The primary commit in a bug fix should have a log message that starts with
'<bz_id> - ', for example ``123456 - fixes a silly bug``.


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
