Merging
=======

Pull Requests
-------------

You have some commits in a branch, and you're ready to merge. The Pulp Team makes
use of pull requests for all but the most trivial contributions. Please have a
look at our :doc:`Contribution checklist <index>`.

On the GitHub page for the repo where your development branch lives, there will be
a "Pull Request" button. Click it. From there you will choose the source and
destination branches.

If there is a bugzilla issue, please title the pull request "<bz_id> -
Short Message". In the comment section below, please include a link to the
issue. Use of GitHub's markdown for the link is prefered. Example:
``[BZ-123456](http://link.tobug)`` Additionally, please also include a link to the
pull request in the bugzilla comments.


For details about using pull requests, see GitHub's
`official documentation <https://help.github.com/articles/using-pull-requests>`_.


Review
------

Once a pull request has been submitted, a member of the team will review it.
That person can indicate their intent to review a particular pull request by
assigning it to themself.

Comments on a pull request are meant to be helpful for the patch author. They
may point out critical flaws, suggest more efficient approaches, express admiration
for your work, ask questions, make jokes, etc. Once review is done, the reviewer
assigns the pull request back to the author. The next step for the author will
go in one of two directions:

1. If you have commit access and can merge the pull request yourself, you can
   take the comments for whatever you think they are worth. Use your own
   judgement, make any revisions you see fit, and merge when you are satisfied.
   Think of the review like having someone proof-read your paper in college.

2. If you are a community member and do not have commit access, we ask that you
   take the review more literally. Since the Pulp Team is accepting responsibility
   for maintaining your code into perpetuity, please address all concerns expressed
   by the reviewer, and assign it back to them when you are done. The reviewer
   will strive to make it clear which issues are blocking your pull request from
   being merged.

.. note::
   *To the community:* The Pulp Team is very grateful for your contribution and
   values your involvement tremendously! There are few things in an OSS project as
   satisfying as receiving a pull request from the community.

   We are very open and honest when we review each other's work. We will do our
   best to review your contribution with respect and professionalism. In return,
   we hope you will accept our review process as an opportunity for everyone to
   learn something, and to make Pulp the best product it can be. If you are
   uncertain about comments or instructions, please let us know!


.. _rebasing-and-squashing:

Rebasing and Squashing
----------------------

Before you submit a pull request, consider an interactive rebase with some
squashing. We prefer each PR to contain a single commit. This offers some
significant advantages:

- Squashing makes it more likely that your merge will be fast-forward only, which
  helps avoid conflicts.
- Nobody wants to see a your typo fixes in the commit log. Consider squashing
  trivial commits so that each commit you merge is as story-focused as possible.
- The ``git commit --amend`` command is very useful, but be sure that you
  `understand what it does <https://www.atlassian.com/git/tutorials/rewriting-history/git-commit--amend>`_
  before you use it! GitHub will update the PR and keep the comments when you force
  push an amended commit.
- Rebasing makes cherry picking features and bug fixes much simpler.

If this is not something that you are comfortable with, an excellent resource can be
found here:

`How to Rebase a Pull Request <https://github.com/edx/edx-platform/wiki/How-to-Rebase-a-Pull-Request>`_

.. warning::
   Keep in mind that rebasing creates new commits that are unique from your
   original commits. Thus, if you have three commits and rebase them, you must
   make sure that all copies of those original commits get deleted. Did you push
   your branch to origin? Delete it and re-push after the rebase.


.. _merging-to-multiple-releases:

Merging to Multiple Releases
----------------------------

The most important aspect of merging a change into multiple release branches is
:ref:`choosing the right branch to start from <choosing-upstream-branch>`.

Once your work is complete, submit a pull request from your GitHub fork into the
branch for the oldest release you intend to merge into. Once review and revision
is complete, merge your branch from the pull request web page. Do not delete the
branch yet.

For cases where there are few merge conflicts, merge your working branch manually
into each successively newer release branch, and finally into master. Generally,
unless you are resolving conflicts or otherwise modifying your initial fix to
accommodate the newer branches, no additional pull requests or review are needed.

For cases where there are substantial merge conflicts whose resolution merits
review, create a new branch from your working branch and merge the release branch
into it. For example, assume you have branch "username-foo" from the "pulp-2.0"
branch.

::

  $ git checkout username-foo
  $ git checkout -b username-foo-merge-2.1
  $ git merge pulp-2.1

At this point you can resolve conflicts, then create a pull request from
username-foo-merge-2.1 into pulp-2.1.


Merging to Old Releases Only
----------------------------

Infrequently, there may be a need to apply a change to an old release but not
newer releases. This should only be a last resort.

One way or another, it is important to merge this change into newer release
branches, even if the actual changes don't get applied. When fixing code that no
longer exists in newer branches, simply do the merge and resolve any conflicts
that arise.

Otherwise, to merge the work but not apply any of its code changes, use merge
strategy "ours".

::

  $ git merge -s ours username-bugfix

In either case, git's history records that your fix has been applied to each
release branch. Make sure the human-readable description of your fix accurately
describes its scope. For example, a good commit message would be
"Fixed memory use issue in ABC system, which was removed in pulp 2.1", or
"Fixed a python 2.4 compatibility issue that is no longer applicable as of pulp
2.2".
