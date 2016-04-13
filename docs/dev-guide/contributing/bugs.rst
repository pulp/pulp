
.. _existing bugs: https://pulp.plan.io/issues?utf8=%E2%9C%93&set_filter=1&f%5B%5D=status_id&op%5Bstatus_id%5D=o&f%5B%5D=tracker_id&op%5Btracker_id%5D=%3D&v%5Btracker_id%5D%5B%5D=1&f%5B%5D=&c%5B%5D=project&c%5B%5D=tracker&c%5B%5D=status&c%5B%5D=priority&c%5B%5D=subject&c%5B%5D=assigned_to&c%5B%5D=updated_on&group_by=

.. _existing stories: https://pulp.plan.io/issues?utf8=%E2%9C%93&set_filter=1&f%5B%5D=status_id&op%5Bstatus_id%5D=o&f%5B%5D=tracker_id&op%5Btracker_id%5D=%3D&v%5Btracker_id%5D%5B%5D=3&f%5B%5D=&c%5B%5D=project&c%5B%5D=tracker&c%5B%5D=status&c%5B%5D=priority&c%5B%5D=subject&c%5B%5D=assigned_to&c%5B%5D=updated_on&group_by=

.. _Prioritized Bugs query: https://pulp.plan.io/issues?query_id=33

.. _Un-Triaged Bugs: https://pulp.plan.io/issues?query_id=30

Bugs
====

All bugs and feature requests (stories) are tracked in
`Pulp's Redmine instance <https://pulp.plan.io/>`_. You can view `existing bugs`_ or
`existing stories`_.

How to file a bug
-----------------

Bugs are one of the main ways that the Pulp team interacts with users
(pulp-list@redhat.com and the #pulp IRC channel being the other methods).

You can `file a new bug or feature request <https://pulp.plan.io/projects/pulp/issues/new>`_.

.. warning::
  Security related bugs need to be marked as private when reported. Use the
  private checkbox (top right) for this.

If you are filing an issue or defect, select ``Issue`` as the *Tracker*. If you
are filing a feature request, select ``Story``.

Fill in the *Subject* and *Description*. Leave the status at ``NEW``. Please
select the closest corresponding *Category*, if any. Select the *Severity* field
and any *Tags* based on your best judgement.

Use the *Version* field to indicate which Pulp version you are using. It has an entry
for each Pulp release (2.0.6, 2.0.7, 2.1.0, etc.). If a bug is found when running
from source instead of a released version, the value ``master`` should be selected.

Use the *OS* field to indicate which Operating System the bug was discovered on.

You can also upload attachments, but please only upload relevant data. For
example, if you have an entire log which contains some errors, please trim it
to just the relevant portions and upload those.

Once a week, the Pulp team triages all new bugs, at which point its
*Severity* rating and other aspects of the report will be evaluated. If
necessary, the bug may be commented on requesting more information or
clarification from the reporter. When a bug has enough information, its
*Priority* rating set and is marked as triaged using the *Triaged* boolean.

Fixing
------

When fixing a bug, all bugs will follow this process, regardless of how trivial.

Developer
^^^^^^^^^

#. Once the bug has been triaged it waits for a developer to pick it up. Generally developers
   should pick bugs from the top of the `Prioritized Bugs query`_.
#. Once a bug is selected, the developer sets themselves as the assignee and also sets the bug
   state to ``ASSIGNED``.
#. The developer creates a new remote branch for the bug on their GitHub fork.
#. When the fix is complete, the developer submits a pull request for the bug into the appropriate
   branch (master, release branch, etc.). It's appreciated by the reviewer if a link to the bug
   is included in the merge request, as well as a brief description of what the change is. It is
   not required to find and assign someone to do the review.
#. When the pull request is submitted, the developer changes the status of the bug to ``POST`` and
   sets the appropriate target release.
#. Wait for someone to review the pull request. The reviewer will assign the pull request back to
   the developer when done and should also ping them through other means. The developer may take
   the reviewer's comments as they see fit and merge the pull request when satisfied. Once merged,
   set bug status to ``MODIFIED``. It is also helpful to include a link to the pull request in a
   comment on the bug.
#. Delete both local and remote branches for the bug.

.. note::
  See :doc:`branching` for more information on how to create branches for bug fixes.

Reviewer
^^^^^^^^
#. When reviewing a pull request, all feedback is appreciated, including compliments, questions,
   and general Python knowledge. It is up to the developer to decide what (if any) changes will
   be made based on each comment.
#. When done reviewing, assign the pull request back to the developer and ping them through
   other means.

Triage Process
--------------

Pulp holds bug triage as an IRC meeting on Fridays at 10:30 ET (either EST or EDT) in #pulp-dev on
Freenode. We encourage bug filers and interested parties to join and give input.

A quorum of at least 2 core developers is required to hold triage. Quorum must be established at
the beginning of the meeting. Developers forming the quorum must stay for the entire duration of
triage or the meeting must be suspended. Triage will be led by the "triage lead" which is a role
that rotates on the 1st of each month. The "triage lead" is responsible for reaching out to other
developers to ensure a quorum can be established.

The triage lead will do the following:

#. Start the meeting by confirming there is a quorum (of which they are 1 person of).
#. Post the link to all `Un-Triaged Bugs`_.
#. For each issue to be triaged, put the URL of the issue being discussed in the chat and
   facilitate an agreement on the priority and severity from anyone in the chat. In cases where
   there is not much feedback, at a minimum the triage lead needs an ack from the other quorum
   member before moving on. If agreement cannot be reached within 1-2 minutes, skip the bug and let
   interested parties post their thoughts on the bug.
#. Update the issue as being triaged. Add any severity and priority changes, component/tag changes,
   and add any comments that come in from the chat. It's preferred for comments to be left directly
   versus having the triage lead leave comments made by others.

Bugs that need additional information will have notes put onto the issue asking for input. Unless a
Redmine user specifically disabled e-mail support, adding a note will e-mail the reporter. Bugs
with enough information and an agreed upon severity and priority, will be triaged. Also any
components or tags should be set.

A target release can also be set during triage. An issue that has target release set during triage
will block a release. Once triaged, the bug is included in the `Prioritized Bugs query`_ and awaits
a developer to pick it up.

The Pulp team uses some additional Tags to help keep track of bugs.

================   ===============================================================
Tag Name           Usage
================   ===============================================================
Documentation      The bug/story itself is documentation related.
EasyFix            A bug that is simple to fix, at least in theory.
SELinux            Indicates it is SELinux related
================   ===============================================================

You may occasionally see discussion in #pulp or on the mailing list about "bug
grooming". This simply means that someone is applying the rules above to
existing bugs that are not new. This is needed from time to time to keep the
bug list up to date.
