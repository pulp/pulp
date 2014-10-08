Bugs
====

Reporting
---------

Bugs must be filed against "Pulp" in the bugzilla entry's *Product* field.

Please try to select the closest corresponding component in the *Components* field.

The *Version* field will have an entry for each Pulp release (2.0.6, 2.0.7, 2.1.0, etc.).
If a bug is found when running from source instead of a released version, the "Master"
value should be selected.

Once a week (typically on Wednesday), the Pulp team triages all new bugs, at which point
the bug may be aligned to a different component and its *Severity* rating will be evaluated.
If necessary, the bug may be marked as ``NEEDINFO`` if more clarification is requested.


Fixing
------

When fixing a bug, all bugs will follow this process, regardless of how trivial.

Developer
^^^^^^^^^

#. Once the bug has been triaged and assigned to a developer, the state of the bug is set to
   ``ASSIGNED``.
#. The developer creates a new remote branch for the bug on their GitHub fork. The name of the
   branch should be the number of the bugzilla entry.
   Example: 123456
#. When the fix is complete, the developer submits a pull request for the bug into the appropriate
   branch (master, release branch, etc.). It's appreciated by the reviewer if a link to the bugzilla
   is included in the merge request, as well as a brief description of what the change is. It is
   not required to find and assign someone to do the review.
#. When the pull request is submitted, the developer changes the status of the bug to ``POST``.
#. Wait for someone to review the pull request. The reviewer will assign the pull request back to
   the developer when done and should also ping them through other means. The developer may take
   the reviewer's comments as they see fit and merge the pull request when satisfied. Once merged,
   set bug status to ``MODIFIED``. It is also helpful to include a link to the pull request in a
   comment on the bug.
#. Delete both local **AND** remote branches for the bug.

Reviewer
^^^^^^^^
#. When reviewing a pull request, all feedback is appreciated, including compliments, questions,
   and general python knowledge. It is up to the developer to decide what (if any) changes will
   be made based on each comment.
#. When done reviewing, assign the pull request back to the developer and ping them through
   other means.

.. note::
  See :doc:`branching` for more information on how to create branches for bug fixes.
