
.. _existing bugs: https://pulp.plan.io/issues?utf8=%E2%9C%93&set_filter=1&f%5B%5D=status_id&op%5Bstatus_id%5D=o&f%5B%5D=tracker_id&op%5Btracker_id%5D=%3D&v%5Btracker_id%5D%5B%5D=1&f%5B%5D=&c%5B%5D=project&c%5B%5D=tracker&c%5B%5D=status&c%5B%5D=priority&c%5B%5D=subject&c%5B%5D=assigned_to&c%5B%5D=updated_on&group_by=

.. _Prioritized Bugs query: https://pulp.plan.io/issues?query_id=33

.. _Un-Triaged Bugs: https://pulp.plan.io/issues?query_id=30

.. _Bugzilla Field Descriptions: https://bugzilla.redhat.com/page.cgi?id=fields.html

Bugs
====

All bugs are tracked in Redmine as an Issue. You can view `existing bugs`_ as examples.

How to file a bug
-----------------

Bugs are one of the main ways that the Pulp team interacts with users
(pulp-list@redhat.com and the #pulp IRC channel being the other methods).

You can `file a new bug <https://pulp.plan.io/projects/pulp/issues/new>`_.

.. warning::
  Is this security related? If so, please follow the `Security Disclosures`_ process.

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

Blocking Bugs
-------------

All Redmine Issues have a "Blocks Release" field. This field refers to upcoming
Platform Release versions that *cannot* be released until this bug is fixed.

For example, if a blocking issues is discovered in Pulp 2.4.6, and 2.4.7 is the next Platform
Release version, then the issue's "Blocks Release" field should be set to ``2.4.z``. If the bug
also affects the next Platform Release of Pulp, such as 2.5.2, the issue's "Block Release" field
should also include ``2.5.z``.

.. _security disclosures:

Security Disclosures
--------------------

We take security issues seriously and welcome responsible disclosure of security vulnerabilities
in Pulp. Please email `pulp-security@redhat.com` (a private address for the Pulp Security Team)
with all reports.

Your report should include:

* Pulp version
* A vulnerability description
* Reproduction steps

Feel free to submit a patch with your disclosure. A member of the Pulp Security Team will confirm
the vulnerability, determine its impact, and develop a fix.

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
   branch (master, release branch, etc.). A link to the bug should be included in the merge request,
   as well as a brief description of what the change is. It is not required to find and assign
   someone to do the review.
#. When the pull request is submitted, the developer changes the status of the bug to ``POST`` and
   includes a link to the open pull request. Pull requests with the ``Work In Progress`` label
   should remain in ``ASSIGNED`` state until the ``Work In Progress`` label is removed.
#. Wait for someone to review the pull request. The reviewer(s) will either approve the pull request
   or request changes that must be addressed before the pull request can be merged. Pull requests
   should have at least one approved review and no reviews requesting changes before being merged.
   Once merged, set the bug status to ``MODIFIED``. If the next platform release version is known,
   set the "Platform Release" field appropriately. Otherwise, leave it blank and it will be set
   during the next platform bugfix release.
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

Pulp holds bug triage as an IRC meeting on Tuesdays and Fridays at 10:30 ET (either EST or EDT) in
#pulp-dev on Freenode. We encourage bug filers and interested parties to join and give input.

A quorum of at least 2 core developers is required to hold triage. Quorum must be established at
the beginning of the meeting. Developers forming the quorum must stay for the entire duration of
triage or the meeting must be suspended. Triage will be led by the "triage lead" which is a role
that rotates on the 1st of each month. The "triage lead" is responsible for reaching out to other
developers to ensure a quorum can be established.

The triage lead will do the following:

#. Announce the meeting in #pulp and #pulp-dev 5 minutes prior to beginning
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

If a bug needs to block a release, the priority should be changed to URGENT. The "Target Platform
Release" field should never be set before the issue is in MODIFIED state.

Bugs that need additional information will have notes put onto the issue asking for input. Unless a
Redmine user specifically disabled e-mail support, adding a note will e-mail the reporter. Bugs
with enough information and an agreed upon severity and priority, will be triaged. Also any
components or tags should be set.

Once triaged, the bug is included in the `Prioritized Bugs query`_ and awaits
a developer to pick it up.

Triage Issue Fields
^^^^^^^^^^^^^^^^^^^

The Priority field represents the order in which issues will be taken from the list of prioritized
bugs, with higher priority issues generally being taken before lower priority issues.

Priorities are defined as follows.

========    ===============================================================================
Priority    Description
========    ===============================================================================
Urgent      Most important. Non-Urgent issues should not be worked on before this issue.
High        Very important, generally worked on after Urgent Priority issues.
Normal      Average importance, generally worked on after High Priority issues.
Low         Not very important, generally worked on after Normal Priorty issues.
========    ===============================================================================

The Severity field represents the impact this issue has on Pulp users.

========    ========================================================================================
Severity    Description
========    ========================================================================================
Urgent      **Catastrophic** issue which severly impacts the operations of an organization
            (including the Pulp team itself), for which there is no workaround. Examples: Pulp can't
            be installed or started as a result of a bug in the latest release, or Pulp is
            destroying user data.
High        Similar to Urgent, this issue severly impacts to operations of an organization, but
            a workaround does exist. Examples: Pulp can only be installed if a certain package is
            manually installed first, or an existing feature of Pulp has suffered a regression.
Medium      Partial but non-critical functionality loss, or other loss of functionality where
            users are still able to perform their critical tasks.
Low         Little or no functionality impact, such as a usage question, or development work.
========    ========================================================================================

Severity is orthogonally related to the Priority field, so it is *possible* (though extremely
unlikely) for an Urgent Priority issue to also be marked as Low Severity.

The values for the Priority and Severity fields are inspired by the values found in Red Hat's
`Bugzilla Field Descriptions`_.

The Pulp team uses some additional Tags to help keep track of bugs.

================   ===============================================================
Tag Name           Usage
================   ===============================================================
Documentation      The bug/story itself is documentation related.
EasyFix            A bug that is simple to fix, at least in theory.
SELinux            Indicates it is SELinux related
================   ===============================================================

Grooming
^^^^^^^^

You may occasionally see discussion in #pulp or on the mailing list about "bug
grooming". This simply means that someone is applying the rules above to
existing bugs that are not new. This is needed from time to time to keep the
bug list up to date.
