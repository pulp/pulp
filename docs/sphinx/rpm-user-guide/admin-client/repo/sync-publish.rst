Repository Synchronization and Publish
======================================

.. _repo-sync:

Synchronization
---------------

Synchronization is the process of downloading repository content (packages,
errata, kickstart trees) into the Pulp server and associating that content
to the repository being synchronized. Not all repositories need to support
sync; it's possible to define a repository without indicating a source feed
and add content to it simply by :ref:`uploading packages <upload-packages>` or
:ref:`copying packages from another repository <copy-packages>`.

A repository sync can be :ref:`triggered immediately <repo-sync-run>` or
:ref:`scheduled <repo-sync-scheduling>` to occur at a later time with an optional
recurrence. An individual repository
can only have at most one sync operation running at any time. If another sync
is requested, either manually or by its schedules, it will be queued up to
execute once all other pending tasks related to that repository have resolved.

For instance, if a repository is in the process of synchronizing and the user
attempts to update the repository's configuration, the update call will be
postponed until the sync finishes. If another sync is requested while the first
is still executing, that second sync call will execute once the first sync
completes and the update takes place.

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
will be displayed.

The ``repo sync status`` command accepts a single required argument:

``--repo-id``
  Identifies the repository being displayed.

.. _repo-sync-scheduling:

Scheduling
^^^^^^^^^^

*TBD*

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

Publish
-------
