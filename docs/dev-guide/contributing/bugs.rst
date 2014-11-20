Bugs
====

The Pulp team uses `Red Hat Bugzilla <https://bugzilla.redhat.com/>`_ for
tracking defects and Requests for Enhancements (RFEs).

How to file a bug
-----------------

Bugs are one of the main ways that the Pulp team interacts with users
(pulp-list@redhat.com and the #pulp IRC channel being the other methods).

To file a bug:

#. Go to `bugzilla <https://bugzilla.redhat.com/>`_ and create an account if
   you do not already have one.
#. After logging in, click on "New" in the upper left corner of the main page.
#. Click "Community" to get a list of community projects and then click "Pulp".
   You can also go `directly <https://bugzilla.redhat.com/enter_bug.cgi?product=Pulp>`_
   to the bug entry page if you like.
#. Enter your bug here. The Pulp team looks through all new bugs at least once
   a week except for during holidays.

The main information to capture is which command you ran, what went wrong, and
what you expected to happen. Please also include the output of ``rpm -qa | grep
pulp | sort`` if possible, and set the *version* field to the corresponding
Pulp version. You can also select a component in the *Components* field if you
have an idea about where the bug should go but this is not
required.

If you are running code off of the master branch, select *master* in the
*version* field.

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

Triaging Bugs
-------------

Once a week, a rotating subset of the Pulp team meets to sort through that
week's new bugs. Bugs that need additional information are marked as "needinfo"
for the reporter. Bugs with enough information will get their severity and
priority set, as well as a component. At this point they are on the backlog and
await a free developer to pick them up.

The Pulp team uses some additional flags to help keep track of bugs.

==============   ===============================================================
Keyword          Usage
==============   ===============================================================
Documentation    Docs bug - these will also be under the Documentation component
EasyFix          A bug that is simple to fix, at least in theory
FutureFeature    A feature request. These usually have "RFE" in the title.
Task             A bug that tracks a task. These are usually to keep track of
                 refactoring ideas or developer setup problems.
Triaged          A bug that has been examined by the triage team.
==============   ===============================================================

You may occasionally see discussion in #pulp or on the mailing list about "bug
grooming". This simply means that someone is applying the rules above to
existing bugs that are not new. This is needed from time to time to keep the
bug list up to date.

