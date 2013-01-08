Merging
=======

Pull Requests
-------------


Merge to Multiple Releases
--------------------------

The most important aspect of merging a change into multiple release branches is
:ref:`choosing the right branch to start from <choosing-upstream-branch>`.

Once your work is complete, submit a pull request into the branch for the oldest
release you intend to merge into. Once review and revision is complete, merge
your branch from the pull request web page. Do not delete the branch yet.

For cases where there are few merge conflicts, merge your working branch manually
into each successively newer release branch, and finally into master.

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


Merge to Old Releases Only
--------------------------

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