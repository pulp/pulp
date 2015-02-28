Bugs
====

Thend feature requests (stories) are tracked in `Pulp's Redmine instance <https://pulp.plan.io/>`_.
You can view `existing bugs <https://pulp.plan.io/issues?utf8=%E2%9C%93&set_filter=1&f%5B%5D=status_id&op%5Bstatus_id%5D=o&f%5B%5D=tracker_id&op%5Btracker_id%5D=%3D&v%5Btracker_id%5D%5B%5D=1&f%5B%5D=&c%5B%5D=project&c%5B%5D=tracker&c%5B%5D=status&c%5B%5D=priority&c%5B%5D=subject&c%5B%5D=assigned_to&c%5B%5D=updated_on&group_by=>`_
or `existing stories <https://pulp.plan.io/issues?utf8=%E2%9C%93&set_filter=1&f%5B%5D=status_id&op%5Bstatus_id%5D=o&f%5B%5D=tracker_id&op%5Btracker_id%5D=%3D&v%5Btracker_id%5D%5B%5D=3&f%5B%5D=&c%5B%5D=project&c%5B%5D=tracker&c%5B%5D=status&c%5B%5D=priority&c%5B%5D=subject&c%5B%5D=assigned_to&c%5B%5D=updated_on&group_by=>`_.

How to file a bug
-----------------

Bugs are one of the main ways that the Pulp team interacts with users
(pulp-list@redhat.com and the #pulp IRC channel being the other methods).

You can `file a new bug or feature request <https://pulp.plan.io/projects/pulp/issues/new>`_.

.. warning::
  Security related bugs need to be marked as private when reported. Use the
  private checkbox (top right) for this. Consider also setting the tag 'Security'.

If you are filing an issue or defect, select ``Issue`` as the *Tracker*. If you
are filing a feature request, select *Story*.

Fill in the *Subject* and *Description*. Leave the status at ``NEW``. Please
select the closest corresponding component, if any, using the *Components*
field. Select the *Severity* field and any tags based on your best judgement.

Use the *Version* field to indicate which Pulp version you are using. It has an entry
for each Pulp release (2.0.6, 2.0.7, 2.1.0, etc.). If a bug is found when running
from source instead of a released version, the value "Master" should be selected.

You can also upload attachments, but please only upload relevant data. For
example, if you have an entire log which contains some errors, please trim it
to just the relevant portions and upload those.

Once a week, the Pulp team triages all new bugs, at which point its
*Severity* rating and other aspects of the report will be evaluated. If
necessary, the bug may be commented in requesting more information or
clarification from the reporter. When a bug has enough information, it has
its *Priority* rating set and is marked as triaged using the 'Triaged' boolean.

Fixing
------

When fixing a bug, all bugs will follow this process, regardless of how trivial.

Developer
^^^^^^^^^

#. Once the bug has been triaged and assigned to a developer, the state of the bug is set to
   ``ASSIGNED``.
#. The developer creates a new remote branch for the bug on their GitHub fork. The name of the
   branch should be the number of the bug entry.
   Example: 123456
#. When the fix is complete, the developer submits a pull request for the bug into the appropriate
   branch (master, release branch, etc.). It's appreciated by the reviewer if a link to the bug
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
 Pulp team uses `Red Hat Bugzilla <https://bugzilla.redhat.com/>`_ for
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

