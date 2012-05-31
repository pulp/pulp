Synchronize and Publish
=======================

.. _repo-sync:

Synchronize
-----------

Synchronization is the process of downloading repository content (packages,
errata, kickstart trees) into the Pulp server and associating that content
to the repository being synchronized. Not all repositories need to support
sync; it's possible to define a repository without indicating a source feed
and add content to it simply by :ref:`uploading packages <upload-packages>` or
:ref:`copying packages from another repository <copy-packages>`.

A repository sync can be :ref:`triggered immediately <repo-sync-run>` or
:ref:`scheduled <repo-sync-scheduling>` to occur at a later time with an optional
recurrence. An individual repository
can only have at most one sync operation running at any time. If a sync is
in progress when attempting to run one, the progress of the running operation
is displayed.

When running a sync, the repository is locked to prevent conflicting changes
from happening while the sync executes.  For instance, if a repository is in the
process of synchronizing and the user attempts to update the repository's
configuration, the update call will be postponed until the sync finishes.

All sync related commands are found in the ``repo sync`` section of the CLI.

.. _repo-sync-run:

Triggering a Manual Sync
^^^^^^^^^^^^^^^^^^^^^^^^

A sync can be triggered using the ``repo sync run`` command. The sync is not
guaranteed to begin immediately. If the server is running at capacity or if
another operation for the repository is being executed, the sync will be
postponed until the earliest possible time it can be run.

When the sync is triggered, the CLI process will remain alive and track the
progress of the sync (:ref:`example output <repo-sync-progress-output>` below).
At any time that progress tracking may be halted by
pressing ctrl+c without affecting the sync process on the server. The progress
tracking can be resumed using the :ref:`status command <repo-sync-status>`.

A repository may only have one running sync operation at a time. Attempting to
trigger another manual sync while one is running will cause the CLI to display
the progress of the already running sync.

The ``repo sync run`` command accepts the following arguments:

``--repo-id``
  Identifies the repository to sync. This argument is required and must refer
  to a valid repository in the Pulp server.

``--bg``
  If specified, the CLI process will end immediately after requesting the server
  perform the sync instead of showing its progress. This has the same effect as
  starting the sync and pressing ctrl+c.

.. _repo-sync-status:

Viewing the Status of a Repository Sync Operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``repo sync status`` command is used to determine is a repository is in the
process of synchronizing. If the repository is being synchronized, the progress
will be displayed (:ref:`example output <repo-sync-progress-output>` below).

The ``repo sync status`` command accepts a single required argument:

``--repo-id``
  Identifies the repository being displayed.

.. _repo-sync-progress-output:

Output
""""""

The following is a sample output for the progress of a repository sync operation::

 +----------------------------------------------------------------------+
                     Synchronizing Repository [proto]
 +----------------------------------------------------------------------+

 This command may be exited by pressing ctrl+c without affecting the actual sync
 operation on the server.

 Downloading metadata...
 [-]
 ... completed

 Downloading repository content...
 [==================================================] 100%
 RPMs:       18/18 items
 Delta RPMs: 0/0 items
 Tree Files: 0/0 items
 Files:      0/0 items
 ... completed

 Importing errata...
 [-]
 ... completed

 Publishing packages...
 [==================================================] 100%
 Packages: 18/18 items
 ... completed

 Publishing distributions...
 [==================================================] 100%
 Distributions: 0/0 items
 ... completed

 Generating metadata
 [\]
 ... completed

 Publishing repository over HTTP
 [-]
 ... completed

 Publishing repository over HTTPS
 [-]
 ... skipped

 Successfully synchronized repository

.. note::
  The above output includes the status of both the sync process and the subsequent
  publishing of the repository. See the :ref:`repo-publish` section for more
  information.

.. _repo-sync-scheduling:

Scheduling
----------

A repository can be configured to synchronize itself in the future and
continue to do so at a specified interval. Schedules are specified in the
ISO8601 specification which is :ref:`described in the conventions section <date-and-time>`
of the user guide.

A schedule is made up of one of the following combinations of elements:

* Interval
* Start Date and Time + Interval
* Recurrence Count + Interval
* Recurrence Count + Start Date and Time + Interval

In the event a start date and time is not specified, the server will default
these values to the moment the server receives the request. In all cases,
an :ref:`interval <date-and-time-interval>` is required.

A repository may have multiple sync schedules in the event a desired schedule
cannot be achieved through intervals alone. For example, in order to synchronize
a repository on the 7th and 21st of every month, two separate schedules with a
one month interval and the appropriate start dates would be defined to meet
these needs.

If a :ref:`recurrence <date-and-time-recurrence>` is specified in the schedule,
only the specified number of sync operations will be triggered from that
schedule. Once all of the runs have been exhausted, regardless of the success or
failure of each run, the schedule will delete itself.

A one-time run in the future (akin to ``at`` system-level functionality) can be
achieved by specifying a recurrence of one. At that point, while the interval
is still required to be specified, it will have no effect and the schedule will
delete itself after its sole execution.

The ``repo sync schedules`` section is the root of all sync schedule related
functionality. The following commands are provided.

.. _repo-sync-schedules-list:

Listing Schedules
^^^^^^^^^^^^^^^^^

All sync schedules for a repository can be displayed using the ``repo sync schedules list``
command. This command takes the following arguments:

``--repo-id``
  Required to identify the repository.

``--details``
  By default only a subset of information about a schedule is displayed. This
  flag will result in more detailed information about each schedule including
  failure threshold and number remaining runs if applicable.

The majority of the information displayed about a sync schedule is self-explanatory.
Below are a few noteworthy items:

* "Remaining Runs" only applies for schedules that are defined with a recurrence
  value. This will indicate not applicable for schedules that do not define a recurrence.

* "Consecutive Failures" works in conjunction with the failure threshold of a
  schedule. Once this value equals the failure threshold, the schedule will
  be disable. If there is no failure threshold configured, this number will still
  continue to reflect the number of consecutive failures.

.. _repo-sync-schedules-create:

Creating a Schedule
^^^^^^^^^^^^^^^^^^^

A new schedule for a repository's sync operation is created through the
``repo sync schedules create`` command which accepts the following arguments:

``--repo-id``
  Required to identify the repository for which to create the schedule

``--schedule``
  ISO8601 string describing the recurrence, start time, and interval. This is
  required when creating a new schedule.

``--failure-threshold``
  If the number of consecutive failures equals this value, the schedule will
  automatically be disabled. If omitted the sync will be allowed to fail
  indefinitely. The schedule may be reenabled later using the :ref:`update command <repo-sync-schedules-update>`.

All schedules are enabled by default when they are created. They may be disabled
using the :ref:`update command <repo-sync-schedules-update>`.

.. _repo-sync-schedules-update:

Updating a Schedule
^^^^^^^^^^^^^^^^^^^

Existing schedules can be edited, both the schedule timings themselves as well
as whether or not the schedule is enabled. The command ``repo sync schedules update``
is used for this purpose.

The following arguments are required when editing a schedule:

``--repo-id``
  Identifies the repository to which the schedule applies.

``--schedule-id``
  Schedule being edited. The ID is found in the :ref:`list schedules command <repo-sync-schedules-list>`.

One or more of the following arguments can be specified to change the schedule:

``--schedule``
  ISO8601 string describing the new schedule timings to use.

``--failure-threshold``
  New failure threshold to use for the schedule. If this value is lower than the
  current consecutive failures count, the sync will still run one more time
  before the failures count is compared against this new value and the schedule
  is disabled.

``--enabled``
  Used to enable or disable the schedule. The value to this argument should be
  either ``true`` or ``false``.

If the repository is currently in the middle of a sync run, the schedule update
will be postponed until after the running sync completes.

Deleting a Schedule
^^^^^^^^^^^^^^^^^^^

Schedules are deleted using the ``repo sync schedules delete`` command. This
command requires the following two arguments:

``--repo-id``
  Repository in which the schedule resides.

``--schedule-id``
  Schedule to delete.

If the repository is currently in the middle of a sync run, the schedule delete
will be postponed until after the running sync completes.

Displaying the Next Scheduled Sync
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When viewing the list of sync schedules for a repository, one of the displayed
fields indicates the next time that schedule will run. If there are multiple
schedules, the client will resolve the next time the sync will run across all
of the schedules through the ``repo sync schedules next`` command.

This command requires the following argument:

``--repo-id``
  Identifies the repository.

The output will indicate both the next schedule sync time and the schedule that
provided that time::

 $ pulp-admin repo sync schedules next --repo-id demo
 The next scheduled run is at 2012-05-31T00:00:00Z driven by the schedule 2012-05-31T00:00:00Z/P1M

For programmatic access to the ISO8601 string indicating the next run time, the
``--quiet`` option may be specified to remove the user-friendly verbiage::

 $ pulp-v2-admin repo sync schedules next --repo-id demo --quiet
 2012-05-31T00:00:00Z


.. _repo-publish:

Publish
-------

Publishing a repository is the process of making its contents available as
a yum repository, either over HTTP, HTTPS, or both depending on the repository's
configuration.

By default, all repositories are automatically published following a successful
sync. However, there are times where it may be desirable to make an explicit
call to publish to expose changes made to the repository's contents. For instance,
if a repository's contents are manipulated by
:ref:`copying packages from another repository <copy-packages>` or by
:ref:`uploading RPMs <upload-packages>` into it, those changes will not be
reflected until a publish operation is run.

All commands related to publishing a repository can be found in the ``repo publish``
section. These commands mirror those found in the ``repo sync`` section, including
the scheduling functionality and output format when displaying the status of
an in progress publish operation. As such, the sync documentation should be
consulted for more information on these commands as they apply to publishing.