Bugs and Feature Requests
=========================

Bugs and feature requests for :term:`pulpcore` are tracked with `Redmine
<https://pulp.plan.io/projects/pulp/issues/>`_. Please see the :ref:`plugin-table` for trackers for
each plugin.

How to file an issue
--------------------

Before you file an issue, please see our :ref:`common-issues` section, hopefully you will be all set. You
also might consider :ref:`connecting with the community<community>`.

You can `file a new bug <https://pulp.plan.io/projects/pulp/issues/new>`_.

.. warning::
  Is this security related? If so, please follow the `Security Disclosures` TODO process.

Redmine Fields
**************

Please set the fields listed here. Fields that are not specified should be left blank


.. list-table::
   :header-rows: 1
   :widths: auto
   :align: center

   * - Field
     - Description

   * - Tracker
     - For a bug, select ``Issue``, for a feature-request, choose ``Story``

   * - Subject
     - Strive to be specific and concise. Please see :ref`good-bugs`

   * - Description
     - This is the most important part! Please see :ref:`good-bugs`

   * - Status
     - Leave this at ``NEW`` unless you would like to fix the issue.

   * - Priority
     - Will be determined during by :ref:`triage`. If set, considered a suggestion.

   * - Category
     - Choose one if applicable, blank is OK.

   * - Sprint/Milestone
     - Internal use, please leave blank.

   * - Severity
     - Will be determined during by :ref:`triage`. If set, considered a suggestion.

   * - Version
     - Version of pulpcore that the filer noticed the issue.

   * - Platform Release
     - Please leave blank.

   * - Blocks Release
     - Please leave blank.

   * - OS
     - Operating system the filer is running.

   * - Tags
     - For searching. Select 0 or many, best judgement.


.. _good-bugs:

Writing Good Issues
*******************

**Subject**
TODO

**Description**
TODO


Fill in the *Subject* and *Description*. Leave the status at ``NEW``. Please
select the closest corresponding *Category*, if any. Select the *Severity* field
and any *Tags* based on your best judgement. (No matter the priority, all bugs will be reviewed in
our :ref:`triage`.)

Use the *Version* field to indicate which Pulp version you are using. It has an entry
for each Pulp release (2.0.6, 2.0.7, 2.1.0, etc.). If a bug is found when running
from source instead of a released version, the value ``master`` should be selected.

Use the *OS* field to indicate which Operating System the bug was discovered on.

You can also upload attachments, but please only upload relevant data. For
example, if you have an entire log which contains some errors, please trim it
to just the relevant portions and upload those.



.. _triage:

Triage
------
Once a week, the Pulp team triages all new bugs, at which point its *Severity* rating and other
aspects of the report will be evaluated. If necessary, the bug may be commented on requesting more
information or clarification from the reporter. When a bug has enough information, its *Priority*
rating set and is marked as triaged using the *Triaged* boolean.
