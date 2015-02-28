Bugs
====

Reporting
---------

Pulp bugs are tracked in `Pulp's Redmine instance <https://pulp.plan.io/>`_.
You can `view existing bugs <https://pulp.plan.io/projects/pulp/issues>`_, or
`file a new bug <https://pulp.plan.io/projects/pulp/issues/new>`_.

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
